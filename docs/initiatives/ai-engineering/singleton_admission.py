"""Fail-closed, OFFLINE-only preflight for a future single Cursor executor.

This module NEVER acquires a lock, launches an agent, or authorizes a merge.
Calling it before acquiring an atomic, durable cross-trigger lease is unsafe.
It evaluates provider/account evidence supplied by a future *trusted* adapter;
self-reported flags or issue text are NOT authority.
"""

from __future__ import annotations

import re
from typing import Any

SHA = re.compile(r"[0-9a-f]{40}\Z")
DECISIONS = frozenset({
    "STOP", "BUSY", "NO_READY_WORK", "OWNER_GATE",
    "REUSE_EXISTING_PR", "READY_FOR_OWNER_DISPATCH",
})


def _result(decision: str, reason: str, *, selected_pr: int | None = None) -> dict[str, Any]:
    assert decision in DECISIONS
    return {
        "decision": decision,
        "reason": reason,
        "selected_pr": selected_pr,
        "launched": False,
        "execution_authorized": False,
    }


def evaluate(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Advisory only, no I/O. Any missing or inconsistent evidence => STOP.

    Snapshot provenance must be validated by caller against live provider/GitHub.
    No boolean in this snapshot is an enforceable account/billing control.
    """
    if not isinstance(snapshot, dict):
        return _result("STOP", "invalid_snapshot")

    # Fail closed before even attempting to select engineering work.
    if snapshot.get("evidence_complete") is not True:
        return _result("STOP", "untrusted_or_incomplete_evidence")
    if snapshot.get("budget_controls_verified") is not True:
        return _result("STOP", "budget_control_unknown")
    if snapshot.get("cursor_on_demand_disabled") is not True:
        return _result("STOP", "paid_overage_possible")
    if snapshot.get("external_billing_excluded") is not True:
        return _result("STOP", "external_billing_unknown")
    if snapshot.get("model_allowlisted") is not True:
        return _result("STOP", "unapproved_model")
    if snapshot.get("subagents_disabled") is not True:
        return _result("STOP", "subagents_not_blocked")
    if snapshot.get("launch_routes_exclusive") is not True:
        return _result("STOP", "uncontrolled_launch_bypass")

    request_id = snapshot.get("request_id")
    if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{8,128}", request_id):
        return _result("STOP", "invalid_request_id")
    previous = snapshot.get("prior_request_ids")
    if not isinstance(previous, list) or any(not isinstance(x, str) for x in previous):
        return _result("STOP", "invalid_idempotency_inventory")
    if request_id in previous:
        return _result("NO_READY_WORK", "duplicate_request")

    # This is an *asserted* admission lease checked offline, not proof of an atomic lock.
    # A separate GitHub-side serial controller must supply authenticated lease state.
    lease = snapshot.get("lease")
    if not isinstance(lease, dict) or lease.get("verified_atomic") is not True:
        return _result("STOP", "atomic_lease_unverified")
    if lease.get("owner_request_id") not in (None, request_id):
        return _result("BUSY", "lease_owned_by_another_request")
    if lease.get("state") not in ("FREE", "OWNED"):
        return _result("STOP", "lease_state_unknown")
    if lease.get("state") == "OWNED" and lease.get("owner_request_id") != request_id:
        return _result("BUSY", "foreign_lease")
    if snapshot.get("provider_run_inventory_complete") is not True:
        return _result("STOP", "provider_run_inventory_incomplete")
    if snapshot.get("ambiguous_previous_launch") is not False:
        return _result("STOP", "ambiguous_prior_launch")
    active_runs = snapshot.get("active_run_ids")
    if not isinstance(active_runs, list) or any(not isinstance(x, str) or not x for x in active_runs):
        return _result("STOP", "invalid_active_run_inventory")
    if active_runs:
        return _result("BUSY", "other_agent_already_active")

    if snapshot.get("scope_authorized") is not True:
        return _result("OWNER_GATE", "scope_not_owner_authorized")
    if snapshot.get("owner_sensitive") is not False:
        return _result("OWNER_GATE", "sensitive_change_requires_owner")
    if type(snapshot.get("attempt_number")) is not int or snapshot["attempt_number"] not in (0, 1, 2):
        return _result("STOP", "retry_limit_or_attempt_unknown")
    if snapshot.get("semantic_reconciliation_accepted") is not True:
        return _result("STOP", "issue_pr_semantics_not_accepted")

    main = snapshot.get("main_sha")
    baseline = snapshot.get("observed_main_sha")
    if not all(isinstance(x, str) and SHA.fullmatch(x) for x in (main, baseline)):
        return _result("STOP", "unverifiable_default_sha")
    if main != baseline:
        return _result("STOP", "stale_default_sha")

    prs = snapshot.get("open_prs")
    if not isinstance(prs, list):
        return _result("STOP", "missing_open_pr_inventory")
    nums = set()
    for pr in prs:
        if not isinstance(pr, dict):
            return _result("STOP", "invalid_pr_inventory")
        num = pr.get("number")
        if type(num) is not int or num <= 0 or num in nums:
            return _result("STOP", "duplicate_or_invalid_pr")
        nums.add(num)
        if pr.get("state") != "OPEN" or pr.get("relation") not in (
            "EXACT_SAME_OUTCOME", "PROPOSED_NOT_ACCEPTED", "PARTIAL",
            "SUPERSEDED_BY_OWNER", "UNRELATED", "INSUFFICIENT_EVIDENCE",
        ):
            return _result("STOP", "pr_relation_or_state_unknown")
        if not isinstance(pr.get("head_sha"), str) or not SHA.fullmatch(pr["head_sha"]):
            return _result("STOP", "unverifiable_pr_head")
        if pr["relation"] == "INSUFFICIENT_EVIDENCE":
            return _result("STOP", "unknown_pr_semantics")
        if pr.get("owner_gate") not in (True, False):
            return _result("STOP", "pr_owner_gate_unknown")
        if pr.get("writer_active") not in (True, False):
            return _result("STOP", "writer_identity_unknown")
        if pr.get("writer_active") is True:
            return _result("BUSY", "pr_writer_active")

    intent = snapshot.get("intent")
    if not isinstance(intent, dict) or intent.get("kind") not in ("INTEGRATE_PR", "NEW_CODE"):
        return _result("STOP", "invalid_work_intent")
    if intent.get("issue_approved") is not True:
        return _result("OWNER_GATE", "unapproved_roadmap_work")
    if intent.get("dependency_evidence_complete") is not True:
        return _result("STOP", "dependency_evidence_missing")

    # Only eligible, relevant PR work preempts new coding. An owner-gated unrelated
    # PR must not deadlock an independently approved, non-overlapping task.
    eligible = [p for p in prs if p["relation"] in ("PROPOSED_NOT_ACCEPTED", "PARTIAL")
                and p.get("integration_ready") is True]
    if any(p.get("integration_ready") not in (True, False) for p in prs):
        return _result("STOP", "integration_readiness_unknown")

    if intent["kind"] == "NEW_CODE":
        if eligible:
            return _result("STOP", "integration_first_existing_pr_ready")
        if any(p["relation"] in ("PROPOSED_NOT_ACCEPTED", "PARTIAL") for p in prs):
            if intent.get("independent_leaf_proven") is not True:
                return _result("OWNER_GATE", "independence_from_blocked_pr_unproven")
        if intent.get("no_overlap_verified") is not True:
            return _result("STOP", "potential_path_or_dependency_overlap")
        return _result("READY_FOR_OWNER_DISPATCH", "new_code_candidate_only")

    target = intent.get("pr_number")
    if type(target) is not int or target not in nums:
        return _result("STOP", "target_pr_not_in_verified_inventory")
    pr = next(p for p in prs if p["number"] == target)
    if pr["relation"] == "EXACT_SAME_OUTCOME":
        return _result("NO_READY_WORK", "outcome_already_accepted")
    if pr["relation"] in ("UNRELATED", "SUPERSEDED_BY_OWNER"):
        return _result("STOP", "unrelated_or_superseded_pr")
    if pr["relation"] not in ("PARTIAL", "PROPOSED_NOT_ACCEPTED"):
        return _result("STOP", "pr_not_integration_candidate")
    if pr.get("owner_gate") is True:
        return _result("OWNER_GATE", "pr_requires_owner_decision", selected_pr=target)
    if pr.get("integration_ready") is not True:
        return _result("STOP", "pr_integration_blocked", selected_pr=target)
    if intent.get("pr_head_sha") != pr["head_sha"]:
        return _result("STOP", "stale_pr_head")
    # No dispatch is actually made or authorized by this result.
    return _result("REUSE_EXISTING_PR", "pr_integration_candidate_only", selected_pr=target)
