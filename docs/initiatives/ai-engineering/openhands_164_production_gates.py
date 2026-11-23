#!/usr/bin/env python3
"""Fail-closed live production gates for #164 (cap attestation, G3 ruleset)."""
from __future__ import annotations

import os


def require_live_provider_cap_workflow_attestation() -> dict | None:
    """Key remaining limit from probe is not trusted global $1 experiment cap by itself."""
    if os.environ.get("AI_ENG_PROVIDER_CAP_STEP_OK") != "1":
        return {
            "decision": "STOP",
            "reason": "provider_cap_workflow_attestation_missing",
            "detail": "same_workflow_run_openrouter_budget_gate_required",
        }
    return None


def require_g3_ruleset_workflow_attestation() -> dict | None:
    if os.environ.get("AI_ENG_G3_RULESET_ATTESTED") != "1":
        return {
            "decision": "STOP",
            "reason": "g3_immutable_ruleset_not_proven",
            "detail": "owner_verified_lease_ruleset_attestation_required",
        }
    return None


def self_test() -> None:
    assert require_live_provider_cap_workflow_attestation()["reason"] == "provider_cap_workflow_attestation_missing"
    assert require_g3_ruleset_workflow_attestation()["reason"] == "g3_immutable_ruleset_not_proven"
    print("PASS: #164 production gates fail-closed without workflow attestation")


if __name__ == "__main__":
    self_test()