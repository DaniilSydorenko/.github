"""Durable owner-controlled ordered task queue (#226), stored in the lease ref tree.

The queue document lives as ``queue.json`` in the tree of the existing
App-custodied ``ai-eng-cursor-lease-v1`` ref. Lease transitions reuse the
observed tree, so they preserve the queue; queue writes reuse the observed
lease state (revision + 1), so they preserve the lease and the replay ledger.
Both serialize on one non-forced ref advance (CAS).

The document separates the immutable authorized ``spec`` (bound to its digest
and to the reviewer-gated workflow run that wrote it) from mutable ``progress``.
A queue document is evidence of an owner decision, not authority by itself:
every write happens only inside the protected owner workflow.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Mapping

from cursor_tasks import DEFAULT_MODEL, CursorTask, validate_registry
from github_ref_lease import LeaseError, RefConflict, Snapshot

QUEUE_FILE = "queue.json"
SCHEMA = 1
MAX_TASKS = 20
ALLOWED_REPOSITORIES = frozenset({
    "DaniilSydorenko/haversine-geolocation",
    "DaniilSydorenko/listing-kit",
    "DaniilSydorenko/engineering-handbook",
})
STATES = ("PENDING", "RUNNING", "DONE", "BLOCKED")
# Progress moves forward only; BLOCKED is terminal until the owner submits a new spec.
TRANSITIONS = {"PENDING": {"RUNNING", "BLOCKED"}, "RUNNING": {"DONE", "BLOCKED"},
               "DONE": set(), "BLOCKED": set()}
QUEUE_ID = re.compile(r"[a-z0-9][a-z0-9-]{2,63}\Z")
CHECK = re.compile(r"[A-Za-z0-9 ._()/:-]{1,100}\Z")
RUN_ID = re.compile(r"[1-9][0-9]{0,19}\Z")
ACTOR = re.compile(r"[A-Za-z0-9-]{1,39}\Z")


class QueueError(LeaseError):
    """Malformed, unauthorized or stale queue: STOP, never fall back."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def spec_digest(spec: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(spec)).hexdigest()


def _tasks(spec: Mapping[str, Any]) -> tuple[CursorTask, ...]:
    out = []
    for t in spec["tasks"]:
        out.append(CursorTask(spec["repository"], t["issue"], t["order"],
                              tuple(t["allowed_paths"]), tuple(t["required_checks"]),
                              default_branch=spec["default_branch"], model=spec["model"],
                              dependencies=tuple(t.get("dependencies", ()))))
    return tuple(out)


def validate_spec(spec: Any) -> tuple[CursorTask, ...]:
    """Return the CursorTasks a spec authorizes, or raise QueueError."""
    try:
        if (not isinstance(spec, dict) or set(spec) != {
                "schema", "queue_id", "repository", "default_branch", "model",
                "accept_subagent_risk", "max_launches", "tasks"}
                or spec["schema"] != SCHEMA
                or not isinstance(spec["queue_id"], str) or not QUEUE_ID.fullmatch(spec["queue_id"])
                or spec["repository"] not in ALLOWED_REPOSITORIES
                or not isinstance(spec["default_branch"], str)
                or not re.fullmatch(r"[A-Za-z0-9._/-]{1,100}", spec["default_branch"])
                or spec["model"] != DEFAULT_MODEL
                or type(spec["accept_subagent_risk"]) is not bool
                or type(spec["max_launches"]) is not int
                or not isinstance(spec["tasks"], list) or not 0 < len(spec["tasks"]) <= MAX_TASKS
                or not 0 < spec["max_launches"] <= len(spec["tasks"])):
            raise QueueError("queue spec shape invalid")
        issues = []
        for t in spec["tasks"]:
            if (not isinstance(t, dict) or not set(t) <= {
                    "issue", "order", "allowed_paths", "required_checks", "dependencies"}
                    or type(t.get("issue")) is not int or type(t.get("order")) is not int
                    or not isinstance(t.get("allowed_paths"), list)
                    or not isinstance(t.get("required_checks"), list) or not t["required_checks"]
                    or any(not isinstance(c, str) or not CHECK.fullmatch(c)
                           for c in t["required_checks"])
                    or len(set(t["required_checks"])) != len(t["required_checks"])
                    or len(set(t["allowed_paths"])) != len(t["allowed_paths"])
                    or not isinstance(t.get("dependencies", []), list)
                    or any(type(d) is not int for d in t.get("dependencies", []))):
                raise QueueError("queue task shape invalid")
            issues.append(t["issue"])
        if [t["order"] for t in spec["tasks"]] != list(range(1, len(spec["tasks"]) + 1)):
            raise QueueError("queue order must be 1..n in list order")
        if len(set(issues)) != len(issues):
            raise QueueError("duplicate issue in queue")
        position = {n: i for i, n in enumerate(issues)}
        for i, t in enumerate(spec["tasks"]):
            for d in t.get("dependencies", []):
                # A dependency must be an earlier task of this queue: no cycles,
                # no forward or foreign dependency the queue cannot satisfy.
                if d not in position or position[d] >= i:
                    raise QueueError("dependency must be an earlier task in this queue")
        tasks = _tasks(spec)
        validate_registry(tasks)
    except QueueError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise QueueError("queue spec invalid: " + type(exc).__name__) from None
    return tasks


def _check_authorization(auth: Any, digest: str) -> None:
    if (not isinstance(auth, dict) or set(auth) != {
            "spec_digest", "workflow_run_id", "actor", "environment"}
            or auth["spec_digest"] != digest
            or not isinstance(auth["workflow_run_id"], str)
            or not RUN_ID.fullmatch(auth["workflow_run_id"])
            or not isinstance(auth["actor"], str) or not ACTOR.fullmatch(auth["actor"])
            or auth["environment"] != "ai-eng-lease-owner"):
        raise QueueError("queue authorization missing or not bound to this spec")


def validate_document(doc: Any) -> tuple[CursorTask, ...]:
    if not isinstance(doc, dict) or set(doc) != {"schema", "spec", "spec_digest",
                                                  "authorization", "progress", "revision"}:
        raise QueueError("queue document shape invalid")
    if doc["schema"] != SCHEMA or type(doc["revision"]) is not int or doc["revision"] < 1:
        raise QueueError("queue document schema or revision invalid")
    tasks = validate_spec(doc["spec"])
    if doc["spec_digest"] != spec_digest(doc["spec"]):
        raise QueueError("queue spec digest mismatch")
    _check_authorization(doc["authorization"], doc["spec_digest"])
    progress = doc["progress"]
    if (not isinstance(progress, dict)
            or set(progress) != {str(t.issue) for t in tasks}
            or any(not isinstance(p, dict) or p.get("state") not in STATES
                   or not isinstance(p.get("evidence"), dict) for p in progress.values())):
        raise QueueError("queue progress invalid")
    if sum(p["state"] == "RUNNING" for p in progress.values()) > 1:
        raise QueueError("more than one RUNNING task")
    return tasks


def load(store: Any, snapshot: Snapshot) -> dict[str, Any] | None:
    """None only when the queue file is genuinely absent; otherwise valid or STOP."""
    raw = store.read_file(snapshot.tree, QUEUE_FILE)
    if raw is None:
        return None
    try:
        doc = json.loads(raw)
    except (ValueError, UnicodeError):
        raise QueueError("queue document is not JSON") from None
    validate_document(doc)
    return doc


def active_tasks(doc: Mapping[str, Any] | None, *, legacy: tuple[CursorTask, ...],
                 legacy_allowed: bool) -> tuple[CursorTask, ...]:
    """Tasks the current run may act on. A malformed queue never reaches here."""
    if doc is not None:
        return validate_document(doc)
    if legacy_allowed:
        return legacy
    raise QueueError("no queue submitted and legacy registry not eligible")


def next_task(doc: Mapping[str, Any]) -> CursorTask | None:
    """First task in owner order that is not DONE; None when the queue is complete.

    A RUNNING or BLOCKED task is returned as-is (it is the head of the queue):
    later tasks never overtake it, and nothing is skipped silently.
    """
    for t in validate_document(doc):
        if doc["progress"][str(t.issue)]["state"] != "DONE":
            return t
    return None


def _write(store: Any, observed: Snapshot, doc: dict[str, Any]) -> str:
    validate_document(doc)
    tree = store.write_tree(observed.tree, QUEUE_FILE,
                            json.dumps(doc, sort_keys=True, indent=1).encode())
    state = copy.deepcopy(observed.state)
    state["revision"] = observed.state["revision"] + 1
    return store.advance(observed, state, tree=tree)


def submit(store: Any, spec: dict[str, Any], *, workflow_run_id: str, actor: str,
           expected_queue_revision: int | None) -> dict[str, Any]:
    """Replace the queue with a newly authorized spec (owner workflow only).

    Only while the lease is IDLE and no queued task is RUNNING. The caller
    names the queue revision it read (None = expect no queue): stale = STOP.
    """
    validate_spec(spec)
    observed = store.read()
    if observed.state["phase"] != "IDLE":
        raise QueueError("queue can change only while the lease is IDLE")
    current = load(store, observed)
    current_rev = None if current is None else current["revision"]
    if current_rev != expected_queue_revision:
        raise QueueError("stale queue revision")
    if current is not None and any(p["state"] == "RUNNING" for p in current["progress"].values()):
        raise QueueError("queue has a RUNNING task")
    digest = spec_digest(spec)
    doc = {"schema": SCHEMA, "spec": copy.deepcopy(spec), "spec_digest": digest,
           "authorization": {"spec_digest": digest, "workflow_run_id": workflow_run_id,
                             "actor": actor, "environment": "ai-eng-lease-owner"},
           "progress": {str(t["issue"]): {"state": "PENDING", "evidence": {}}
                        for t in spec["tasks"]},
           "revision": (current_rev or 0) + 1}
    _write(store, observed, doc)
    return doc


def reorder(store: Any, issue_order: list[int], *, workflow_run_id: str, actor: str,
            expected_queue_revision: int) -> dict[str, Any]:
    """New order for PENDING tasks; a new spec digest needs this run's authorization.

    Tasks that are not PENDING keep their position, so an executed or blocked
    prefix can never be rewritten.
    """
    observed = store.read()
    if observed.state["phase"] != "IDLE":
        raise QueueError("queue can change only while the lease is IDLE")
    current = load(store, observed)
    if current is None or current["revision"] != expected_queue_revision:
        raise QueueError("stale queue revision")
    old = current["spec"]["tasks"]
    by_issue = {t["issue"]: t for t in old}
    if sorted(issue_order) != sorted(by_issue) or len(set(issue_order)) != len(issue_order):
        raise QueueError("reorder must be a permutation of the queued issues")
    for i, t in enumerate(old):
        if current["progress"][str(t["issue"])]["state"] != "PENDING" and issue_order[i] != t["issue"]:
            raise QueueError("only PENDING tasks can move")
    spec = copy.deepcopy(current["spec"])
    spec["tasks"] = [{**copy.deepcopy(by_issue[n]), "order": i + 1}
                     for i, n in enumerate(issue_order)]
    validate_spec(spec)  # dependencies must still point to earlier tasks
    digest = spec_digest(spec)
    doc = {**copy.deepcopy(current), "spec": spec, "spec_digest": digest,
           "authorization": {"spec_digest": digest, "workflow_run_id": workflow_run_id,
                             "actor": actor, "environment": "ai-eng-lease-owner"},
           "revision": current["revision"] + 1}
    _write(store, observed, doc)
    return doc


def set_progress(store: Any, issue: int, state: str, evidence: Mapping[str, Any], *,
                 expected_spec_digest: str) -> dict[str, Any]:
    """Controller progress update; keeps spec and authorization unchanged.

    Retries after a CAS conflict only by re-reading: never overwrites a newer
    document, and refuses if the authorized spec changed underneath.
    """
    for _ in range(3):
        observed = store.read()
        current = load(store, observed)
        if current is None or current["spec_digest"] != expected_spec_digest:
            raise QueueError("queue spec changed; progress not recorded")
        entry = current["progress"].get(str(issue))
        if entry is None:
            raise QueueError("issue is not in the queue")
        if entry["state"] == state:
            return current  # idempotent (workflow retry)
        if state not in TRANSITIONS[entry["state"]]:
            raise QueueError(f"illegal progress {entry['state']} -> {state}")
        doc = copy.deepcopy(current)
        doc["progress"][str(issue)] = {"state": state, "evidence": dict(evidence)}
        doc["revision"] = current["revision"] + 1
        try:
            _write(store, observed, doc)
            return doc
        except RefConflict:
            continue
    raise QueueError("queue progress write kept conflicting; stop")

