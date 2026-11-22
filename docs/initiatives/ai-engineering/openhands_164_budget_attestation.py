#!/usr/bin/env python3
"""Strict provider-side shared $1 cap attestation for #164 (re-probe, fail-closed)."""
from __future__ import annotations

from typing import Any, Callable

from openrouter_budget_gate import probe as default_probe
from openhands_runner_admission_bridge import ProviderBudgetAttestation

REQUIRED_PROBE_REASON = "provider_key_limit_verified"


def attest_shared_provider_cap(
    api_key: str,
    *,
    probe: Callable[[str], dict[str, Any]] = default_probe,
) -> tuple[ProviderBudgetAttestation | None, dict[str, Any] | None]:
    """Re-probe OpenRouter; never treat workflow-only or cached probes as PASS."""
    if not isinstance(api_key, str) or not api_key.startswith("sk-or-"):
        return None, {"decision": "STOP", "reason": "missing_or_unexpected_provider_key"}
    verdict = probe(api_key)
    if verdict.get("decision") != "PASS":
        return None, {
            "decision": "STOP",
            "reason": "provider_shared_cap_not_proven",
            "probe_reason": verdict.get("reason"),
        }
    if verdict.get("reason") != REQUIRED_PROBE_REASON:
        return None, {
            "decision": "STOP",
            "reason": "provider_cap_semantics_unverified",
            "probe_reason": verdict.get("reason"),
        }
    if verdict.get("live_execution_authorized") is True:
        return None, {"decision": "STOP", "reason": "probe_must_not_authorize_execution"}
    return ProviderBudgetAttestation(
        verified_within_shared_cap=True,
        attestation_source="trusted_workflow_budget_probe",
    ), None


def self_test() -> None:
    ok = lambda _k: {"decision": "PASS", "reason": REQUIRED_PROBE_REASON, "live_execution_authorized": False}
    att, err = attest_shared_provider_cap("sk-or-offline", probe=ok)
    assert err is None and att is not None and att.verified_within_shared_cap
    _, bad = attest_shared_provider_cap("sk-or-offline", probe=lambda _k: {"decision": "STOP", "reason": "x"})
    assert bad["reason"] == "provider_shared_cap_not_proven"
    _, sem = attest_shared_provider_cap("sk-or-offline", probe=lambda _k: {"decision": "PASS", "reason": "other"})
    assert sem["reason"] == "provider_cap_semantics_unverified"
    _, miss = attest_shared_provider_cap("")
    assert miss["reason"] == "missing_or_unexpected_provider_key"
    print("PASS: #164 strict provider cap attestation")


if __name__ == "__main__":
    self_test()