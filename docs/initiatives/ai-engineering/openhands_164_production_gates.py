#!/usr/bin/env python3
"""API-backed production gates for #164 live pilot (env booleans never sufficient)."""
from __future__ import annotations

import os
from typing import Any, Callable

from lease_ruleset_candidate import public_readonly_probe
from openrouter_budget_gate import probe as openrouter_probe
from openhands_runner_admission_bridge import ProviderBudgetAttestation

REQUIRED_PROBE_REASON = "provider_key_limit_verified"
HQ_REPO_API = "https://api.github.com/repos/DaniilSydorenko/.github"
FORGED_ENV_KEYS = ("AI_ENG_PROVIDER_CAP_STEP_OK", "AI_ENG_G3_RULESET_ATTESTED")


class _HqGitHubReader:
    def __init__(self, token: str, transport: Callable[[str, str, str], Any]):
        self._token = token
        self._transport = transport

    def get(self, path: str):
        return self._transport("GET", HQ_REPO_API + path, self._token)


def _resolve_writer_app_id() -> tuple[int | None, dict[str, Any] | None]:
    raw = os.environ.get("AI_ENG_WRITER_APP_ID") or os.environ.get("AI_ENG_APPROVED_WRITER_APP_ID", "")
    if isinstance(raw, str) and raw.isdecimal() and 0 < int(raw) <= 9_999_999_999_999:
        return int(raw), None
    return None, {
        "decision": "STOP",
        "reason": "g3_writer_app_id_unconfigured",
        "detail": "set_AI_ENG_WRITER_APP_ID_from_authenticated_github_app_inventory",
    }


def _reject_forged_env_flags(*, probe_passed: bool, g3_status: str | None) -> dict[str, Any] | None:
    """Caller-controlled env flags cannot substitute for provider/GitHub API proof."""
    if os.environ.get("AI_ENG_PROVIDER_CAP_STEP_OK") == "1" and not probe_passed:
        return {"decision": "STOP", "reason": "forged_provider_cap_env_rejected"}
    if os.environ.get("AI_ENG_G3_RULESET_ATTESTED") == "1" and g3_status != "CANDIDATE":
        return {"decision": "STOP", "reason": "forged_g3_ruleset_env_rejected"}
    return None


def verify_provider_hard_cap(
    api_key: str,
    *,
    probe=openrouter_probe,
) -> tuple[ProviderBudgetAttestation | None, dict[str, Any] | None, dict[str, Any]]:
    """Bind to live OpenRouter key response; remaining balance alone is insufficient."""
    if not isinstance(api_key, str) or not api_key.startswith("sk-or-"):
        return None, {"decision": "STOP", "reason": "missing_or_unexpected_provider_key"}, {}
    verdict = probe(api_key)
    probe_passed = verdict.get("decision") == "PASS" and verdict.get("reason") == REQUIRED_PROBE_REASON
    forged = _reject_forged_env_flags(probe_passed=probe_passed, g3_status=None)
    if forged is not None:
        return None, forged, verdict
    if not probe_passed:
        return None, {
            "decision": "STOP",
            "reason": "provider_shared_cap_not_proven",
            "probe_reason": verdict.get("reason"),
            "detail": "provider_enforced_key_limit_required_not_workflow_env",
        }, verdict
    if verdict.get("live_execution_authorized") is True:
        return None, {"decision": "STOP", "reason": "probe_must_not_authorize_execution"}, verdict
    attestation = ProviderBudgetAttestation(
        verified_within_shared_cap=True,
        attestation_source="trusted_workflow_budget_probe",
    )
    return attestation, None, verdict


def verify_g3_lease_ruleset(
    read_token: str,
    *,
    transport: Callable[[str, str, str], Any],
) -> dict[str, Any] | None:
    app_id, err = _resolve_writer_app_id()
    if err is not None:
        return err
    assert app_id is not None
    audit = public_readonly_probe(_HqGitHubReader(read_token, transport), app_id)
    status = audit.get("status")
    forged = _reject_forged_env_flags(probe_passed=False, g3_status=status if isinstance(status, str) else None)
    if forged is not None:
        return forged
    if status != "CANDIDATE":
        return {
            "decision": "STOP",
            "reason": "g3_immutable_ruleset_not_proven",
            "ruleset_audit_status": status,
            "ruleset_audit_reason": audit.get("reason"),
            "detail": "authenticated_github_ruleset_probe_required",
        }
    return None


def self_test() -> None:
    class FakeReader:
        def get(self, path):
            if path.endswith("/ai-eng-cursor-lease-v1"):
                return {"name": "ai-eng-cursor-lease-v1", "protected": False, "commit": {"sha": "a" * 40}}
            raise ValueError(path)

    assert verify_g3_lease_ruleset("tok", transport=lambda *a: FakeReader().get(a[1].split(".github")[-1]))[
        "reason"
    ] in ("g3_writer_app_id_unconfigured", "g3_immutable_ruleset_not_proven")
    os.environ["AI_ENG_G3_RULESET_ATTESTED"] = "1"
    try:
        denied = _reject_forged_env_flags(probe_passed=False, g3_status="STOP")
        assert denied["reason"] == "forged_g3_ruleset_env_rejected"
    finally:
        os.environ.pop("AI_ENG_G3_RULESET_ATTESTED", None)
    print("PASS: #164 production gates reject forged env without API proof")


if __name__ == "__main__":
    self_test()