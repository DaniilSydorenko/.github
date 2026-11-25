#!/usr/bin/env python3
"""API-backed production gates for #164 live pilot (env booleans never sufficient)."""
from __future__ import annotations

import os
import json
import re
import sys
from typing import Any, Callable

from lease_ruleset_candidate import public_readonly_probe, audit as audit_rulesets, REF
from openhands_lease_admission_adapter import RulesetEvidence
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


_G3_REASON = "ruleset_shape_passed_live_bypass_and_cas_proofs_still_required"


def _g3_binding(issue: int) -> dict | None:
    env = os.environ
    app_id, err = _resolve_writer_app_id()
    if (err or app_id != 5535339 or issue not in (217, 226)
            or env.get("GITHUB_REPOSITORY") != "DaniilSydorenko/.github"
            or env.get("GITHUB_ACTOR") != "DaniilSydorenko"
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
            or env.get("GITHUB_RUN_ATTEMPT") != "1"
            or env.get("AI_ENG_OWNER_GO_ISSUE") != str(issue)
            or not re.fullmatch(r"[0-9a-f]{40}", env.get("GITHUB_SHA", ""))
            or not re.fullmatch(r"[1-9][0-9]*", env.get("GITHUB_RUN_ID", ""))):
        return None
    return {"schema": 1, "repository": env["GITHUB_REPOSITORY"],
            "sha": env["GITHUB_SHA"], "run_id": env["GITHUB_RUN_ID"],
            "attempt": 1, "issue": issue, "writer_app_id": app_id}


def _expected_g3_audit() -> dict:
    return {"status": "CANDIDATE", "reason": _G3_REASON,
                      "candidate_only": True, "cursor_launch_authorized": False,
                      "model_runs_started": 0, "github_mutated": False}


def emit_g3_evidence() -> int:
    from lease_ruleset_candidate import ReadOnly
    raw_issue = os.environ.get("AI_ENG_OWNER_GO_ISSUE", "")
    binding = _g3_binding(int(raw_issue)) if raw_issue in ("217", "226") else None
    token = os.environ.get("GITHUB_TOKEN", "")
    output = os.environ.get("GITHUB_OUTPUT", "")
    if not binding or not token or not output:
        print("STOP: missing protected audit context or credential")
        return 2
    reader = ReadOnly(token)
    class RecordingReader:
        def __init__(self):
            self.responses = {}
        def get(self, path):
            value = reader.get(path)
            self.responses[path] = value
            return value
    recording = RecordingReader()
    audit = public_readonly_probe(recording, binding["writer_app_id"])
    print(json.dumps(audit, sort_keys=True))
    if json.dumps(audit, sort_keys=True) != json.dumps(_expected_g3_audit(), sort_keys=True):
        return 2
    branch = recording.responses.get(f"/branches/{REF}")
    rulesets = [v for k, v in recording.responses.items() if re.fullmatch(r"/rulesets/[1-9][0-9]*", k)]
    if audit_rulesets(branch, rulesets, approved_app_id=binding["writer_app_id"]) != audit:
        return 2
    # Retain only fields consumed by the verifier; never transfer credentials.
    branch = {k: branch[k] for k in ("name", "protected", "commit")}
    branch["commit"] = {"sha": branch["commit"]["sha"]}
    rulesets = [{k: rule[k] for k in ("id", "target", "source_type", "source", "enforcement", "conditions", "rules", "bypass_actors") if k in rule} for rule in rulesets]
    evidence = {**binding, "audit": audit, "branch": branch, "rulesets": rulesets}
    with open(output, "a", encoding="utf-8") as stream:
        stream.write("evidence=" + json.dumps(evidence, separators=(",", ":")) + "\n")
    return 0


def verify_isolated_g3_evidence(issue: int) -> dict | None:
    # Authenticity is the protected workflow's needs output, not a signature.
    # Never expose the administrative credential to this runner.
    if "AI_ENG_RULESET_AUDIT_TOKEN" in os.environ:
        return {"decision": "STOP", "reason": "privileged_audit_token_in_live_runner"}
    if os.environ.get("AI_ENG_G3_RULESET_ATTESTED"):
        return {"decision": "STOP", "reason": "forged_g3_ruleset_env_rejected"}
    binding = _g3_binding(issue)
    raw = os.environ.get("AI_ENG_G3_EVIDENCE", "")
    try:
        evidence = json.loads(raw) if len(raw) <= 65536 else None
    except (ValueError, TypeError):
        evidence = None
    expected = {**binding, "audit": _expected_g3_audit()} if binding else None
    # Canonical JSON comparison also rejects bool/int type confusion.
    if not isinstance(evidence, dict) or expected is None or json.dumps({k: v for k, v in evidence.items() if k not in ("branch", "rulesets")}, sort_keys=True) != json.dumps(expected, sort_keys=True):
        return {"decision": "STOP", "reason": "g3_isolated_evidence_invalid"}
    if audit_rulesets(evidence.get("branch"), evidence.get("rulesets"), approved_app_id=binding["writer_app_id"]) != _expected_g3_audit():
        return {"decision": "STOP", "reason": "g3_isolated_inventory_invalid"}
    return None


def isolated_ruleset_evidence(issue: int) -> RulesetEvidence:
    if verify_isolated_g3_evidence(issue) is not None:
        raise PermissionError("g3_isolated_evidence_invalid")
    evidence = json.loads(os.environ["AI_ENG_G3_EVIDENCE"])
    return RulesetEvidence(evidence["branch"], evidence["rulesets"], evidence["writer_app_id"], True)


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
    if sys.argv[1:] == ["--emit-g3"]:
        sys.exit(emit_g3_evidence())
    self_test()