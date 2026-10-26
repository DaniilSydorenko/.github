"""Deterministic, fail-closed Cursor terminal-run and PR verification (Issue #120).

This verifier performs NO I/O and grants NO model launch, next-Issue dispatch,
merge, deployment, lease release, or spending authority. Its input is an
untrusted/previously observed snapshot: a separate authenticated controller
must collect GitHub and provider evidence and revalidate it before acting.

Stages covered: terminal provider run -> exact-head PR checks -> bounded
correction *proposal* -> owner acceptance *observation*. No auto-correction.
"""
from __future__ import annotations

import re
from typing import Any

SHA = re.compile(r"[0-9a-f]{40}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
REQUEST = re.compile(r"[A-Za-z0-9_.:-]{8,128}\Z")
AGENT = re.compile(r"bc-[0-9a-fA-F-]{36}\Z")
RUN = re.compile(r"run-[0-9a-fA-F-]{36}\Z")
TERMINAL = frozenset(("FINISHED", "ERROR", "CANCELLED", "EXPIRED"))
ACTIVE = frozenset(("CREATING", "RUNNING", "WAITING_FOR_BACKGROUND_WORK"))
CHECK_CONCLUSIONS = frozenset(("success", "failure", "cancelled", "timed_out", "skipped"))
CHECK_PENDING = frozenset(("queued", "in_progress", "pending"))
RESULTS = frozenset((
    "STOP", "WAIT_RUN", "WAIT_PR", "WAIT_CI", "CORRECTION_REVIEW",
    "OWNER_GATE", "ACCEPTED_OBSERVED",
))


def _sha(x: Any) -> bool:
    return isinstance(x, str) and SHA.fullmatch(x) is not None


def _positive(x: Any) -> bool:
    return type(x) is int and x > 0


def _paths(value: Any) -> bool:
    return (isinstance(value, list) and len(value) > 0 and len(value) <= 80
            and all(isinstance(p, str) and p and len(p) <= 250
                    and not p.startswith("/") and "\\" not in p and
                    not any(segment in (".", "..") for segment in p.split("/"))
                    for p in value) and len(value) == len(set(value)))


def _out(status: str, reason: str, *, corrections_remaining: int | None = None) -> dict:
    assert status in RESULTS
    return {
        "status": status, "reason": reason,
        "corrections_remaining": corrections_remaining,
        "advisory_only": True, "provider_called": False,
        "model_runs_started": 0, "automatic_merge": False,
        "new_model_invocation_authorized": False,
        "next_issue_authorized": False, "release_lease_authorized": False,
        "charged_cost": "UNKNOWN",
    }


def verify_execution(snapshot: dict[str, Any]) -> dict[str, Any]:
    """One bounded execution evidence assessment, without side effects."""
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1:
        return _out("STOP", "invalid_snapshot_schema")
    task = snapshot.get("task")
    lease = snapshot.get("lease")
    provider = snapshot.get("provider")
    pr = snapshot.get("pr")
    checks = snapshot.get("checks")
    attempts = snapshot.get("attempts")
    acceptance = snapshot.get("acceptance")
    if not all(isinstance(x, dict) for x in (task, lease, provider, pr, attempts, acceptance)):
        return _out("STOP", "missing_execution_evidence")
    repo, issue, number = task.get("repository"), task.get("issue_number"), task.get("pr_number")
    request = task.get("request_id")
    if (not isinstance(repo, str) or not REPO.fullmatch(repo)
            or any(t in (".", "..") for t in repo.split("/"))
            or not _positive(issue) or not _positive(number)
            or not isinstance(request, str) or not REQUEST.fullmatch(request)
            or task.get("pr_url") != f"https://github.com/{repo}/pull/{number}"
            or task.get("owner_authority") not in ("verified", "missing", "unknown")
            or task.get("scope_authority") not in ("verified", "missing", "unknown")
            or not _paths(task.get("allowed_paths"))
            or not isinstance(task.get("required_checks"), list)
            or not 0 < len(task["required_checks"]) <= 16
            or any(not isinstance(v, str) or not v or len(v) > 120
                   for v in task["required_checks"])
            or len(task["required_checks"]) != len(set(task["required_checks"]))):
        return _out("STOP", "task_scope_or_check_contract_invalid")
    if task["scope_authority"] != "verified" or task["owner_authority"] != "verified":
        return _out("STOP", "owner_or_domain_permission_unverified")

    if (lease.get("phase") not in ("RUNNING", "VERIFYING")
            or lease.get("request_id") != request
            or lease.get("pr_url") != task["pr_url"]
            or not _positive(lease.get("revision"))
            or lease.get("observed_revision") != lease["revision"]):
        return _out("STOP", "wrong_or_stale_owned_global_lease")

    agent_id, run_id = provider.get("agent_id"), provider.get("run_id")
    run = provider.get("run")
    if (not isinstance(agent_id, str) or not AGENT.fullmatch(agent_id)
            or not isinstance(run_id, str) or not RUN.fullmatch(run_id)
            or lease.get("agent_id") != agent_id or lease.get("run_id") != run_id
            or not isinstance(run, dict)
            or run.get("id") != run_id or run.get("agentId") != agent_id
            or provider.get("observation_complete") is not True
            or provider.get("other_active_run") is not False):
        return _out("STOP", "run_identity_or_global_inventory_unverified")
    state = run.get("status")
    if state in ACTIVE:
        if lease["phase"] != "RUNNING":
            return _out("STOP", "running_provider_conflicts_with_verifying_lease")
        return _out("WAIT_RUN", "cursor_run_not_terminal")
    if state not in TERMINAL:
        return _out("STOP", "unknown_provider_run_state")
    if state != "FINISHED":
        return _out("STOP", "cursor_run_failed_cancelled_or_expired")
    if lease["phase"] != "VERIFYING":
        # Terminal status observed: owner-controlled transition to VERIFYING,
        # NOT release, must be recorded first.
        return _out("WAIT_RUN", "terminal_run_not_yet_in_verifying_phase")

    # Correction history is an independent source of cumulative spending.
    # No auto-reset after newer HEAD; at most two evidence-backed corrections.
    history = attempts.get("corrections")
    if attempts.get("initial_run_verified") is not True or not isinstance(history, list):
        return _out("STOP", "attempt_history_unverified")
    if len(history) > 2:
        return _out("STOP", "correction_limit_exceeded")
    known_runs = {run_id}
    for i, item in enumerate(history, 1):
        if (not isinstance(item, dict) or item.get("index") != i
                or not _sha(item.get("failure_head"))
                or not isinstance(item.get("evidence_ref"), str)
                or not item["evidence_ref"].startswith(f"https://github.com/{repo}/")
                or not isinstance(item.get("run_id"), str)
                or not RUN.fullmatch(item["run_id"])
                or item["run_id"] in known_runs):
            return _out("STOP", "correction_history_duplicate_or_unproven")
        known_runs.add(item["run_id"])
    remaining = 2 - len(history)

    if pr.get("number") != number or pr.get("url") != task["pr_url"]:
        return _out("STOP", "pr_identity_mismatch")
    if pr.get("state") == "missing":
        # A completed provider run might publish its PR asynchronously.
        # At most three cheap observations; never wake a model to poll.
        ticks = pr.get("observations_after_terminal")
        if (pr.get("lookup_complete") is True and type(ticks) is int
                and 0 <= ticks < 3):
            return _out("WAIT_PR", "provider_finished_pr_not_yet_visible")
        return _out("STOP", "pr_missing_or_wait_budget_exhausted")

    if pr.get("state") not in ("open", "closed"):
        return _out("STOP", "pr_state_unknown")
    if (not _sha(pr.get("head_sha"))
            or pr.get("head_sha") != pr.get("observed_head_sha")
            or not _sha(pr.get("base_sha"))
            or pr.get("base_sha") != pr.get("observed_base_sha")
            or pr.get("changed_paths_complete") is not True
            or not _paths(pr.get("changed_paths"))):
        return _out("STOP", "pr_head_base_or_files_unverified")
    if not set(pr["changed_paths"]).issubset(set(task["allowed_paths"])):
        return _out("STOP", "changed_paths_outside_authorized_scope")

    # Exact-head checks MUST be verified even after a PR is merged. A merge
    # event, successful provider run or closed Issue cannot replace CI proof.
    if not isinstance(checks, list) or len(checks) > 40:
        return _out("STOP", "checks_inventory_unbounded")
    indexed = {}
    for check in checks:
        if (not isinstance(check, dict) or not isinstance(check.get("name"), str)
                or not check["name"] or check["name"] in indexed
                or check.get("head_sha") != pr["head_sha"]
                or check.get("conclusion") not in CHECK_CONCLUSIONS | CHECK_PENDING
                or check.get("observed") is not True):
            return _out("STOP", "unknown_or_stale_exact_head_check")
        indexed[check["name"]] = check
    missing = any(name not in indexed for name in task["required_checks"])
    statuses = [indexed[name]["conclusion"] for name in task["required_checks"]
                if name in indexed]
    pending = any(x in CHECK_PENDING for x in statuses)
    failed = any(x != "success" for x in statuses)

    if pr["state"] == "open":
        if pr.get("merged") is not False:
            return _out("STOP", "contradictory_open_merged_state")
        if missing:
            return _out("WAIT_CI", "required_exact_head_checks_missing")
        if pending:
            return _out("WAIT_CI", "required_checks_pending")
        if failed:
            if remaining <= 0:
                return _out("STOP", "correction_budget_exhausted",
                            corrections_remaining=0)
            # Correction candidate only, independently owner/budget gated.
            if attempts.get("failure_evidence_verified") is not True:
                return _out("STOP", "failed_checks_without_bounded_diagnostic",
                            corrections_remaining=remaining)
            return _out("CORRECTION_REVIEW", "evidenced_failed_exact_head_check",
                        corrections_remaining=remaining)
        if acceptance.get("issue_criteria") == "pending":
            return _out("OWNER_GATE", "issue_acceptance_not_yet_proven",
                        corrections_remaining=remaining)
        if acceptance.get("issue_criteria") != "accepted":
            return _out("STOP", "issue_acceptance_unknown",
                        corrections_remaining=remaining)
        return _out("OWNER_GATE", "merge_and_domain_acceptance_still_required",
                    corrections_remaining=remaining)

    # Closed/merged PR: a pending/failed/missing check is a hard STOP, not
    # evidence that production acceptance or new model work is safe.
    if pr.get("merged") is not True:
        return _out("STOP", "closed_unmerged_or_unknown_pr")
    if missing or pending or failed:
        return _out("STOP", "merged_pr_required_checks_not_proven")
    if (not _sha(pr.get("merge_sha"))
            or pr.get("merged_into_default_proven") is not True
            or acceptance.get("issue_criteria") != "accepted"
            or acceptance.get("owner_merge") != "approved"):
        return _out("STOP", "merged_pr_without_authenticated_acceptance")
    if acceptance.get("deployment") == "pending":
        return _out("OWNER_GATE", "deployment_acceptance_pending")
    if acceptance.get("device") == "pending":
        return _out("OWNER_GATE", "device_acceptance_pending")
    if (acceptance.get("deployment") not in ("accepted", "not_required")
            or acceptance.get("device") not in ("accepted", "not_required")):
        return _out("STOP", "deployment_or_device_acceptance_unknown")
    # Even here, controller must separately prove safe, owner-approved release
    # of the exact lease and next request. Observation != grant.
    return _out("ACCEPTED_OBSERVED", "complete_but_release_requires_separate_owner_gate",
                corrections_remaining=remaining)
