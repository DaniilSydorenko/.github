#!/usr/bin/env python3
"""Read-only/offline lease-to-OpenHands admission adapter for #164 (D2 slice).

Maps independently attested lease CAS state, exact HEAD pins, writer identity,
and optional ruleset evidence into a fail-closed STOP outcome. This module
never acquires or releases a lease, calls OpenHands/models, spends provider
budget, performs GitHub writes, or dispatches workflows.

Wiring target: a trusted workflow supplies fresh evidence; the live runner
calls this adapter immediately before any model credential handoff. A green
offline result is necessary shape checks only, not live authorization.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from github_ref_lease import LeaseError, agent_id_for, check_state
from lease_ruleset_candidate import audit as ruleset_audit

try:
    from openhands_164_lease_preconditions import (
        AdmissionDenied,
        Context,
        validate_lease_snapshot,
    )
except ImportError:  # main until #166 merges; adapter stays STOP-closed.
    AdmissionDenied = RuntimeError  # type: ignore[misc, assignment]

    @dataclass(frozen=True)
    class Context:  # type: ignore[no-redef]
        issue: int
        request_id: str
        target_sha: str
        workflow_run_id: str
        expected_lease_sha: str

    def validate_lease_snapshot(*_a: Any, **_k: Any) -> str:
        raise AdmissionDenied("lease_preconditions_module_unavailable")

SHA = re.compile(r"[0-9a-f]{40}\Z")
ISSUES = (216, 217, 226)
REPO = "https://github.com/DaniilSydorenko/haversine-geolocation"
HQ_LEASE_REF = "ai-eng-cursor-lease-v1"


@dataclass(frozen=True)
class LeaseRefEvidence:
    """Authenticated read of the durable CAS ref.

    Boolean flags are workflow-attested shape inputs from a trusted verifier.
    They are not independent live authorization and never set openhands_authorized.
    """

    observed_ref_head_sha: str
    snapshot_commit_sha: str
    state: dict[str, Any]
    authenticated_ref: bool
    exclusive_writer_verified: bool
    credential_path_verified: bool


@dataclass(frozen=True)
class TargetHeadEvidence:
    """Pinned task base vs fresh default-branch observations."""

    pinned_target_sha: str
    initial_default_head_sha: str
    rechecked_default_head_sha: str
    head_inventory_authenticated: bool


@dataclass(frozen=True)
class WriterIdentityEvidence:
    attested_writer_agent_id: str
    workflow_attests_writer_matches_lease: bool


@dataclass(frozen=True)
class RulesetEvidence:
    """Offline injection of lease_ruleset_candidate audit inputs."""

    branch: dict[str, Any]
    rulesets: list[dict[str, Any]]
    approved_app_id: int
    inventory_complete: bool


@dataclass(frozen=True)
class AdmissionRequest:
    issue: int
    workflow_run_id: str
    expected_lease_sha: str
    lease: LeaseRefEvidence
    target_head: TargetHeadEvidence
    writer: WriterIdentityEvidence
    ruleset: RulesetEvidence | None = None  # None is always STOP; never optional live path


def _stop(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "decision": "STOP",
        "reason": reason,
        "openhands_authorized": False,
        "model_invoked": False,
        "github_write": False,
        "lease_acquired": False,
        **extra,
    }


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def request_id_for(issue: int) -> str:
    if issue not in ISSUES:
        raise ValueError("issue_out_of_scope")
    return f"openhands-164-issue-{issue}"


def evaluate_ruleset_evidence(ruleset: RulesetEvidence | None) -> dict[str, Any] | None:
    if ruleset is None:
        return _stop("ruleset_evidence_missing")
    if not ruleset.inventory_complete:
        return _stop("ruleset_inventory_incomplete")
    audited = ruleset_audit(
        ruleset.branch,
        ruleset.rulesets,
        approved_app_id=ruleset.approved_app_id,
    )
    status = audited.get("status")
    if status == "STOP":
        return _stop("immutable_ref_protection_unknown", ruleset_audit=audited)
    if status != "CANDIDATE":
        return _stop("ruleset_audit_status_not_candidate", ruleset_audit=audited)
    return None


def evaluate_target_head(target: TargetHeadEvidence) -> dict[str, Any] | None:
    if not target.head_inventory_authenticated:
        return _stop("target_head_not_authenticated")
    for label, value in (
        ("pinned_target_sha", target.pinned_target_sha),
        ("initial_default_head_sha", target.initial_default_head_sha),
        ("rechecked_default_head_sha", target.rechecked_default_head_sha),
    ):
        if not _valid_sha(value):
            return _stop("unverifiable_" + label)
    if target.initial_default_head_sha != target.rechecked_default_head_sha:
        return _stop("default_head_changed_during_admission")
    if target.pinned_target_sha != target.rechecked_default_head_sha:
        return _stop("stale_or_replayed_target_sha")
    return None


def evaluate_lease_ref_alignment(lease: LeaseRefEvidence, expected_lease_sha: str) -> dict[str, Any] | None:
    if not lease.authenticated_ref:
        return _stop("lease_ref_not_authenticated")
    if not _valid_sha(expected_lease_sha):
        return _stop("expected_lease_sha_invalid")
    if not _valid_sha(lease.observed_ref_head_sha):
        return _stop("observed_lease_ref_sha_invalid")
    if not _valid_sha(lease.snapshot_commit_sha):
        return _stop("lease_snapshot_sha_invalid")
    if lease.observed_ref_head_sha != lease.snapshot_commit_sha:
        return _stop("lease_ref_head_snapshot_mismatch")
    if lease.observed_ref_head_sha != expected_lease_sha:
        return _stop("lease_ref_sha_missing_or_stale")
    if not lease.exclusive_writer_verified or not lease.credential_path_verified:
        return _stop("operational_security_not_verified")
    try:
        check_state(lease.state)
    except LeaseError:
        return _stop("lease_state_invalid")
    return None


def evaluate_writer_identity(lease: LeaseRefEvidence, writer: WriterIdentityEvidence) -> dict[str, Any] | None:
    rid = lease.state.get("request_id")
    if not isinstance(rid, str):
        return _stop("lease_request_identity_missing")
    expected = agent_id_for(rid)
    if lease.state.get("agent_id") != expected:
        return _stop("lease_agent_identity_inconsistent")
    if not isinstance(writer.attested_writer_agent_id, str) or not writer.attested_writer_agent_id.startswith("bc-"):
        return _stop("writer_identity_unverified")
    if writer.attested_writer_agent_id != expected:
        return _stop("writer_identity_mismatch")
    if not writer.workflow_attests_writer_matches_lease:
        return _stop("writer_attestation_missing")
    return None


def evaluate_preconditions(
    lease: LeaseRefEvidence,
    issue: int,
    workflow_run_id: str,
    expected_lease_sha: str,
    target_sha: str,
) -> dict[str, Any] | None:
    ctx = Context(
        issue=issue,
        request_id=lease.state.get('request_id'),
        target_sha=target_sha,
        workflow_run_id=workflow_run_id,
        expected_lease_sha=expected_lease_sha,
    )
    try:
        validate_lease_snapshot(
            lease.state,
            ctx,
            observed_lease_sha=lease.observed_ref_head_sha,
            authenticated_ref=lease.authenticated_ref,
            exclusive_writer_verified=lease.exclusive_writer_verified,
            credential_path_verified=lease.credential_path_verified,
        )
    except AdmissionDenied as exc:
        return _stop(str(exc))
    except Exception:
        return _stop("admission_precondition_error")
    return None


def _evaluate_admission_inner(request: AdmissionRequest) -> dict[str, Any]:
    """Ordered, lazy evaluation: each gate runs only if earlier gates passed."""
    if request.issue not in ISSUES:
        return _stop("issue_out_of_scope")
    loops = (
        lambda: evaluate_ruleset_evidence(request.ruleset),
        lambda: evaluate_target_head(request.target_head),
        lambda: evaluate_lease_ref_alignment(request.lease, request.expected_lease_sha),
        lambda: evaluate_writer_identity(request.lease, request.writer),
        lambda: evaluate_preconditions(
            request.lease,
            request.issue,
            request.workflow_run_id,
            request.expected_lease_sha,
            request.target_head.pinned_target_sha,
        ),
    )
    for run in loops:
        step = run()
        if step is not None:
            return step
    return _stop(
        "openhands_admission_preconditions_shape_ok_not_live_authorization",
        lease_ref=HQ_LEASE_REF,
        issue=request.issue,
        request_id=request.lease.state.get('request_id'),
    )


def evaluate_admission(request: AdmissionRequest) -> dict[str, Any]:
    """Fail-closed admission mapping; never authorizes OpenHands execution."""
    if not isinstance(request, AdmissionRequest):
        return _stop("untrusted_admission_request")
    try:
        return _evaluate_admission_inner(request)
    except Exception:
        return _stop("admission_evaluation_failed")


def self_test() -> None:
    head = "a" * 40
    lease_sha = "b" * 40
    ok_ruleset = RulesetEvidence(
        branch={"name": HQ_LEASE_REF, "protected": True, "commit": {"sha": lease_sha}},
        rulesets=[],
        approved_app_id=1,
        inventory_complete=False,
    )
    bad = evaluate_admission(
        AdmissionRequest(
            216,
            "12345",
            lease_sha,
            LeaseRefEvidence(lease_sha, lease_sha, {}, False, False, False),
            TargetHeadEvidence(head, head, head, False),
            WriterIdentityEvidence("bc-invalid", False),
            ok_ruleset,
        )
    )
    assert bad["decision"] == "STOP"
    print("PASS: openhands lease admission adapter offline negatives (not live GO)")


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["--self-test"]:
        self_test()
    else:
        print("Usage: openhands_lease_admission_adapter.py [--self-test]", file=sys.stderr)
        sys.exit(2)