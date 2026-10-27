"""Offline-testable GitHub fast-forward ref lease for one managed Cursor agent.

NOT wired to Actions or Cursor. The GitHub ref is a monotonic commit chain.
A non-forced ref advance is the atomic compare-and-swap: sibling commits
cannot both fast-forward the same ref. Never automatically expire leases.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PREFIX = "AI_ENG_CURSOR_LEASE_V1\n"
SHA = re.compile(r"[0-9a-f]{40}\Z")
REQ = re.compile(r"[A-Za-z0-9_.:-]{8,128}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
MAX_CONSUMED_REQUESTS = 256  # Never evict history automatically; stop instead.
PHASES = {"IDLE", "RESERVED", "DISPATCHING", "RUNNING", "VERIFYING", "BLOCKED"}


class LeaseError(RuntimeError):
    """Unknown state/transport/permission: stop; never dispatch."""


class RefConflict(LeaseError):
    """Another actor advanced the state ref first."""


@dataclass(frozen=True)
class Snapshot:
    sha: str
    tree: str
    state: dict[str, Any]


class Store(Protocol):
    def read(self) -> Snapshot: ...
    def advance(self, observed: Snapshot, state: dict[str, Any]) -> str: ...


def check_state(s: dict[str, Any]) -> None:
    if not isinstance(s, dict) or s.get("version") != 1 or s.get("phase") not in PHASES:
        raise LeaseError("invalid lease state")
    if s["phase"] == "IDLE":
        if (s.get("request_id") is not None or s.get("agent_id") is not None
                or s.get("source_issue_url") is not None):
            raise LeaseError("idle state still has an owner")
    else:
        if not isinstance(s.get("request_id"), str) or not REQ.fullmatch(s["request_id"]):
            raise LeaseError("lease owner missing")
        if not isinstance(s.get("agent_id"), str) or not s["agent_id"].startswith("bc-"):
            raise LeaseError("agent identity missing")
        source = s.get("source_issue_url")
        target = s.get("pr_url")
        if source is not None:
            if (not isinstance(source, str) or not re.fullmatch(
                    r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/[1-9][0-9]*", source)
                    or not isinstance(target, str)
                    or not re.fullmatch(
                        r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(?:pull|issues)/[1-9][0-9]*",
                        target)
                    or target.split("/")[3:5] != source.split("/")[3:5]):
                raise LeaseError("issue-origin lease target mismatch")
    if type(s.get("revision")) is not int or s["revision"] < 0:
        raise LeaseError("bad state revision")
    fingerprints = s.get("consumed_request_hashes")
    if (not isinstance(fingerprints, list) or len(fingerprints) > MAX_CONSUMED_REQUESTS
            or any(not isinstance(x, str) or not DIGEST.fullmatch(x) for x in fingerprints)
            or len(fingerprints) != len(set(fingerprints))):
        # Existing pre-ledger refs must be explicitly reconciled/migrated,
        # never auto-assumed empty; unknown replay history is a hard STOP.
        raise LeaseError("missing, malformed, or exhausted replay ledger")
    if s["phase"] != "IDLE" and fingerprint(s["request_id"]) not in fingerprints:
        raise LeaseError("active request missing from persistent replay ledger")


def initial_state() -> dict[str, Any]:
    return {"version": 1, "revision": 0, "phase": "IDLE", "request_id": None,
            "agent_id": None, "run_id": None, "pr_url": None,
            "consumed_request_hashes": []}


def agent_id_for(request_id: str) -> str:
    if not isinstance(request_id, str) or not REQ.fullmatch(request_id):
        raise LeaseError("invalid request identity")
    return "bc-" + str(uuid.uuid5(uuid.NAMESPACE_URL, "ai-eng-cursor-v1:" + request_id))


def fingerprint(request_id: str) -> str:
    if not isinstance(request_id, str) or not REQ.fullmatch(request_id):
        raise LeaseError("invalid request identity")
    return hashlib.sha256(("ai-eng-cursor-request-v1:" + request_id).encode()).hexdigest()


class Controller:
    """Mutations are all CAS; never retries a failed or ambiguous launch."""

    def __init__(self, store: Store):
        self.store = store

    def acquire(self, request_id: str, pr_url: str) -> str:
        """Reserve exactly one scoped work item: existing PR or new Issue.

        For an Issue origin, pr_url is initially the issue URL; when the
        provider and GitHub independently prove the generated PR, it is bound
        via bind_generated_pr, preserving immutable source_issue_url.
        """
        agent_id = agent_id_for(request_id)
        if not isinstance(pr_url, str) or not re.fullmatch(
            r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(?:pull|issues)/[1-9][0-9]*", pr_url
        ):
            raise LeaseError("invalid scoped work URL")
        old = self.store.read()
        check_state(old.state)
        if old.state["phase"] != "IDLE":
            return "ALREADY_OWNED" if old.state["request_id"] == request_id else "BUSY"
        used = old.state["consumed_request_hashes"]
        if fingerprint(request_id) in used:
            return "ALREADY_CONSUMED"  # Never make even one more Cursor POST.
        if len(used) >= MAX_CONSUMED_REQUESTS:
            return "HISTORY_FULL"  # Owner must redesign capacity; never evict.
        nxt = {**old.state, "revision": old.state["revision"] + 1,
               "phase": "RESERVED", "request_id": request_id, "agent_id": agent_id,
               "pr_url": pr_url, "run_id": None,
               "source_issue_url": pr_url if "/issues/" in pr_url else None,
               "consumed_request_hashes": [*used, fingerprint(request_id)]}
        try:
            self.store.advance(old, nxt)
        except RefConflict:
            return "RACE_LOST"   # caller may read next state; MUST NOT invoke Cursor
        return "ACQUIRED"

    def transition(self, request_id: str, from_phase: str, to_phase: str,
                   *, run_id: str | None = None) -> str:
        allowed = {
            ("RESERVED", "DISPATCHING"), ("DISPATCHING", "RUNNING"),
            ("DISPATCHING", "BLOCKED"), ("RUNNING", "VERIFYING"),
            ("RUNNING", "BLOCKED"), ("VERIFYING", "BLOCKED"),
            ("VERIFYING", "IDLE"), ("BLOCKED", "IDLE"),
            ("RESERVED", "IDLE"),
        }
        if (from_phase, to_phase) not in allowed:
            raise LeaseError("forbidden transition")
        if to_phase == "RUNNING" and (not isinstance(run_id, str) or not run_id.startswith("run-")):
            raise LeaseError("run id required")
        old = self.store.read()
        check_state(old.state)
        if old.state["request_id"] != request_id or old.state["phase"] != from_phase:
            raise LeaseError("owner/phase mismatch")
        if to_phase == "IDLE" and from_phase != "RESERVED":
            # A terminal Cursor run and owner-authorized accepted integration are
            # external facts: proof must be attested by a separate trusted gate.
            raise LeaseError("release requires externally verified terminal/owner acceptance")
        nxt = {**old.state, "revision": old.state["revision"] + 1, "phase": to_phase}
        if to_phase == "RUNNING":
            nxt["run_id"] = run_id
        if to_phase == "IDLE":
            nxt = {**initial_state(), "revision": nxt["revision"],
                   "consumed_request_hashes": list(old.state["consumed_request_hashes"])}
        self.store.advance(old, nxt)
        return to_phase

    def bind_generated_pr(self, request_id: str, *, expected_issue_url: str,
                          generated_pr_url: str) -> str:
        """Bind a single generated PR once in VERIFYING.

        Caller MUST independently verify provider run git PR association and
        GitHub Issue/PR identity from authenticated fresh reads. This pure CAS
        method cannot authenticate those external facts by itself. It cannot
        grant next-Issue dispatch, lease release, billing or owner acceptance.
        """
        if not isinstance(generated_pr_url, str) or not re.fullmatch(
                r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/[1-9][0-9]*",
                generated_pr_url):
            raise LeaseError("invalid generated PR URL")
        old = self.store.read()
        check_state(old.state)
        source = old.state.get("source_issue_url")
        if (old.state["phase"] != "VERIFYING"
                or old.state.get("request_id") != request_id
                or source != expected_issue_url
                or old.state.get("pr_url") != source
                or not isinstance(source, str)
                or generated_pr_url.split("/")[3:5] != source.split("/")[3:5]):
            raise LeaseError("generated PR not owned by verifying issue lease")
        nxt = {**old.state, "revision": old.state["revision"] + 1,
               "pr_url": generated_pr_url}
        self.store.advance(old, nxt)
        return "BOUND_PR"

    def release_verified(self, request_id: str, *, provider_terminal: bool,
                         integration_accepted: bool, manual_approval: bool) -> str:
        # V1 deliberately requires explicit manual recovery/acceptance.
        if not (provider_terminal and integration_accepted and manual_approval):
            raise LeaseError("release proof incomplete")
        old = self.store.read()
        check_state(old.state)
        if old.state["request_id"] != request_id or old.state["phase"] not in ("VERIFYING", "BLOCKED"):
            raise LeaseError("release not in terminal verification phase")
        nxt = {**initial_state(), "revision": old.state["revision"] + 1,
               "consumed_request_hashes": list(old.state["consumed_request_hashes"])}
        self.store.advance(old, nxt)
        return "RELEASED"


class GitHubRefStore:
    """GitHub Git Data REST adapter. Only use in authenticated, serial controller.

    Branch must be bootstrapped by an owner; absent/malformed ref is STOP.
    The state lives in each commit message, never in a mutable Issue comment.
    """

    def __init__(self, repo: str, token: str, ref: str = "ai-eng-cursor-lease-v1"):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise LeaseError("invalid repository")
        if not re.fullmatch(r"[a-z][a-z0-9-]{3,80}", ref):
            raise LeaseError("invalid ref")
        if not token:
            raise LeaseError("missing GitHub authorization")
        self.api = "https://api.github.com/repos/" + repo
        self.ref = ref
        self.token = token

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        req = Request(
            self.api + path,
            data=None if body is None else json.dumps(body, sort_keys=True).encode(),
            method=method,
            headers={"Authorization": "Bearer " + self.token,
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28",
                     "Content-Type": "application/json"},
        )
        try:
            with urlopen(req, timeout=12) as resp:
                return json.load(resp)
        except HTTPError as e:
            if e.code in (409, 422) and method == "PATCH":
                raise RefConflict("non-fast-forward or ref race") from None
            raise LeaseError(f"GitHub HTTP {e.code} on {method} (no body exposed)") from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise LeaseError("GitHub request/response unknown; stop") from None

    def read(self) -> Snapshot:
        ref = self._call("GET", "/git/ref/heads/" + self.ref)
        sha = ref.get("object", {}).get("sha")
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise LeaseError("invalid ref commit")
        commit = self._call("GET", "/git/commits/" + sha)
        msg = commit.get("message", "")
        tree = commit.get("tree", {}).get("sha")
        if not isinstance(msg, str) or not msg.startswith(PREFIX):
            raise LeaseError("unrecognized ref state")
        if not isinstance(tree, str) or not SHA.fullmatch(tree):
            raise LeaseError("invalid ref tree")
        try:
            state = json.loads(msg[len(PREFIX):])
        except (ValueError, TypeError):
            raise LeaseError("malformed state") from None
        check_state(state)
        return Snapshot(sha, tree, state)

    def advance(self, observed: Snapshot, state: dict[str, Any]) -> str:
        check_state(state)
        check_state(observed.state)
        if not SHA.fullmatch(observed.sha) or not SHA.fullmatch(observed.tree):
            raise LeaseError("invalid previous commit")
        if state["revision"] != observed.state["revision"] + 1:
            raise LeaseError("non-monotonic revision")
        prior = observed.state["consumed_request_hashes"]
        current = state["consumed_request_hashes"]
        if current[:len(prior)] != prior or len(current) not in (len(prior), len(prior) + 1):
            raise LeaseError("persistent replay ledger rollback or invalid append")
        if len(current) == len(prior) + 1:
            if (observed.state["phase"] != "IDLE" or state["phase"] != "RESERVED"
                    or current[-1] != fingerprint(state["request_id"])):
                raise LeaseError("request history append without new owned admission")
        message = PREFIX + json.dumps(state, sort_keys=True, separators=(",", ":"))
        new_commit = self._call("POST", "/git/commits", {
            "message": message, "tree": observed.tree, "parents": [observed.sha]
        })
        sha = new_commit.get("sha")
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise LeaseError("commit create outcome unknown; stop")
        # Only one sibling child of 'observed.sha' can fast-forward the shared ref.
        # No forced overwrite, and no automatic retry when the result is unknown.
        self._call("PATCH", "/git/refs/heads/" + self.ref, {"sha": sha, "force": False})
        return sha
