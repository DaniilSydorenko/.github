#!/usr/bin/env python3
"""Offline integration contract: issue -> inventory -> patch -> publisher STOP.

No GitHub writes, no credentials, no model calls, no live admission.
"""
from __future__ import annotations
import json
import pathlib
import tempfile
from openhands_live_orchestrator import EXPECTED
from openhands_164_patch_contract import ALLOWED, verify_workspace_change
from openhands_runner_admission_bridge import evaluate_before_model_handoff


def integration_gate(issue, inventory, patch_verdict, admission):
    if type(issue) is not int or issue != 216:
        return {"decision": "STOP", "reason": "unexpected_issue"}
    if inventory.get("reason") != "live_authorization_not_integrated":
        return {"decision": "STOP", "reason": "inventory_not_verified"}
    if inventory.get("issues") != [{"number": n, "target": p} for n, p in EXPECTED]:
        return {"decision": "STOP", "reason": "queue_mismatch"}
    if patch_verdict.get("decision") != "PATCH_SCOPE_VERIFIED" or patch_verdict.get("target") != ALLOWED[216]:
        return {"decision": "STOP", "reason": "patch_scope_unverified"}
    if patch_verdict.get("base_sha") != inventory.get("default_head"):
        return {"decision": "STOP", "reason": "base_sha_mismatch"}
    if (admission.get("decision") != "STOP"
            or admission.get("model_credential_handoff") is not False
            or admission.get("openhands_authorized") is not False
            or admission.get("reason") != "missing_trusted_workflow_attestation"):
        return {"decision": "STOP", "reason": "admission_not_fail_closed"}
    return {"decision": "STOP", "reason": "protected_lease_and_publisher_not_integrated",
            "issue": 216, "patch_scope_verified": True, "model_invoked": False,
            "github_write": False, "publish_authorized": False}


def self_test():
    import subprocess
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit",
                        "--allow-empty", "-qm", "base"], check=True)
        sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        target = root / ALLOWED[216]
        target.parent.mkdir(parents=True)
        target.write_text("Supported Node 22 and 24; Node 26 forward smoke is not minimum support.\n")
        patch = verify_workspace_change(root, sha, 216)
        inventory = {"reason": "live_authorization_not_integrated", "default_head": sha,
                     "issues": [{"number": n, "target": p} for n, p in EXPECTED]}
        admission = evaluate_before_model_handoff(216, "test", trusted_attestation=None,
                                                   budget_attestation=None)
        result = integration_gate(216, inventory, patch, admission)
        assert result["reason"] == "protected_lease_and_publisher_not_integrated"
        assert not result["model_invoked"] and not result["github_write"]
        assert integration_gate(217, inventory, patch, admission)["reason"] == "unexpected_issue"
        assert integration_gate(216, inventory, {**patch, "base_sha": "b" * 40}, admission)["reason"] == "base_sha_mismatch"
        assert integration_gate(216, inventory, {**patch, "target": ALLOWED[217]}, admission)["reason"] == "patch_scope_unverified"
        assert integration_gate(216, inventory, patch, {"decision": "GO", "model_credential_handoff": True})["reason"] == "admission_not_fail_closed"
        assert integration_gate(216, inventory, patch, {"decision": "STOP", "model_credential_handoff": False, "openhands_authorized": False, "reason": "arbitrary"})["reason"] == "admission_not_fail_closed"
        assert integration_gate(216, {**inventory, "issues": []}, patch, admission)["reason"] == "queue_mismatch"
        print(json.dumps({"test": "issue216_integration_contract", "decision": "PASS",
                          "live_admission": "BLOCKED", "model_invoked": False,
                          "github_write": False}, sort_keys=True))


if __name__ == "__main__":
    self_test()
