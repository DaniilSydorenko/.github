#!/usr/bin/env python3
"""Offline bridge from trusted workflow evidence to lease admission (not live GO).

Demonstrates how a protected runner would invoke ``evaluate_admission`` only
after independently attested evidence is injected. This module never hands off
model credentials, never acquires leases, and never parses caller JSON into
security attestations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from openhands_lease_admission_adapter import (
    AdmissionRequest,
    LeaseRefEvidence,
    RulesetEvidence,
    TargetHeadEvidence,
    WriterIdentityEvidence,
    evaluate_admission,
)

# Keys a runner or issue body must never use to self-attest trust boundaries.
CALLER_FORBIDDEN_ATTESTATION_KEYS = frozenset({
    "exclusive_writer_verified",
    "credential_path_verified",
    "authenticated_ref",
    "head_inventory_authenticated",
    "workflow_attests_writer_matches_lease",
    "inventory_complete",
    "ruleset",
    "rulesets",
    "approved_app_id",
    "budget_controls_verified",
    "provider_budget_verified",
    "remaining_budget_usd",
    "remaining_spend_usd",
    "live_openhands_capability_verified",
    "openhands_authorized",
    "model_credential_handoff",
})


@dataclass(frozen=True)
class TrustedWorkflowAttestation:
    """Workflow-injected evidence bundle. Never build from runner/caller JSON."""

    expected_lease_sha: str
    lease: LeaseRefEvidence
    target_head: TargetHeadEvidence
    writer: WriterIdentityEvidence
    ruleset: RulesetEvidence


@dataclass(frozen=True)
class ProviderBudgetAttestation:
    """Separate provider-cap attestation from a trusted budget probe, not JSON."""

    verified_within_shared_cap: bool
    attestation_source: str


def _stop(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "decision": "STOP",
        "reason": reason,
        "model_credential_handoff": False,
        "live_openhands_capability_verified": False,
        "openhands_authorized": False,
        **extra,
    }


def _forbidden_keys_present(value: object, *, found: set[str] | None = None) -> set[str]:
    if found is None:
        found = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key in CALLER_FORBIDDEN_ATTESTATION_KEYS:
                found.add(key)
            _forbidden_keys_present(item, found=found)
    elif isinstance(value, list):
        for item in value:
            _forbidden_keys_present(item, found=found)
    return found


def caller_json_carries_forbidden_attestation(payload: object) -> set[str]:
    if not isinstance(payload, Mapping):
        return set()
    return _forbidden_keys_present(payload)


def to_admission_request(
    issue: int,
    workflow_run_id: str,
    trusted: TrustedWorkflowAttestation,
) -> AdmissionRequest:
    return AdmissionRequest(
        issue=issue,
        workflow_run_id=workflow_run_id,
        expected_lease_sha=trusted.expected_lease_sha,
        lease=trusted.lease,
        target_head=trusted.target_head,
        writer=trusted.writer,
        ruleset=trusted.ruleset,
    )


def finalize_pre_model_handoff(adapter_verdict: dict[str, Any]) -> dict[str, Any]:
    """Always STOP before model credentials until live capability is proven elsewhere."""
    reason = str(adapter_verdict.get("reason", "unknown"))
    if adapter_verdict.get("decision") != "STOP":
        reason = "adapter_returned_non_stop"
    elif reason == "openhands_admission_preconditions_shape_ok_not_live_authorization":
        reason = "model_handoff_blocked_live_capability_unverified"
    return {
        **adapter_verdict,
        "decision": "STOP",
        "reason": reason,
        "model_credential_handoff": False,
        "live_openhands_capability_verified": False,
        "openhands_authorized": False,
    }


def evaluate_before_model_handoff(
    issue: int,
    workflow_run_id: str,
    *,
    trusted_attestation: TrustedWorkflowAttestation | None,
    budget_attestation: ProviderBudgetAttestation | None,
    caller_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Runner entry: map trusted evidence to adapter; never authorize model use."""
    forbidden = caller_json_carries_forbidden_attestation(caller_context or {})
    if forbidden:
        return _stop("caller_attestation_fields_not_trusted", forbidden_keys=sorted(forbidden))
    if trusted_attestation is None:
        return _stop("missing_trusted_workflow_attestation")
    if budget_attestation is None:
        return _stop("missing_provider_budget_attestation")
    if not budget_attestation.verified_within_shared_cap:
        return _stop("provider_budget_not_verified")
    if budget_attestation.attestation_source != "trusted_workflow_budget_probe":
        return _stop("provider_budget_attestation_source_untrusted")
    request = to_admission_request(issue, workflow_run_id, trusted_attestation)
    return finalize_pre_model_handoff(evaluate_admission(request))


def self_test() -> None:
    payload = {"issue": 216, "exclusive_writer_verified": True}
    assert caller_json_carries_forbidden_attestation(payload) == {"exclusive_writer_verified"}
    verdict = evaluate_before_model_handoff(216, "1", trusted_attestation=None, budget_attestation=None)
    assert verdict["reason"] == "missing_trusted_workflow_attestation"
    assert verdict["model_credential_handoff"] is False
    print("PASS: runner admission bridge rejects caller attestation and missing trust (offline)")


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["--self-test"]:
        self_test()
    else:
        print("Usage: openhands_runner_admission_bridge.py [--self-test]", file=sys.stderr)
        sys.exit(2)