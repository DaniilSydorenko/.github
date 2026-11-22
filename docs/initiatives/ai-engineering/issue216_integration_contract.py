#!/usr/bin/env python3
"""Offline integration contract: issue → inventory → patch → publisher STOP.

No GitHub writes, no credentials, no model calls, no live admission.
"""
from __future__ import annotations
import json
import pathlib
import subprocess
import tempfile

from openhands_live_orchestrator import EXPECTED
from openhands_164_patch_contract import ALLOWED, verify_workspace_change
from openhands_runner_admission_bridge import evaluate_before_model_handoff
from openhands_164_live_wiring import TERMINAL_WIRED, LiveWiringRequest, run_protected_live_wiring
from openhands_164_vertical_integration import TERMINAL_OFFLINE, VerticalRequest, run_offline_vertical
from test_github_ref_lease import MemoryGitRef
from test_openhands_runner_admission_bridge import BUDGET_OK, trusted_bundle


def integration_gate(issue, inventory, patch_verdict, admission, *, vertical=None, live_wiring=None):
    """Legacy gate plus optional full vertical replay when ``vertical`` is supplied."""
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
    if vertical is None and live_wiring is None:
        return {"decision": "STOP", "reason": "protected_lease_and_publisher_not_integrated",
                "issue": 216, "patch_scope_verified": True, "model_invoked": False,
                "github_write": False, "publish_authorized": False}
    if vertical is not None:
        if vertical.get("reason") != TERMINAL_OFFLINE:
            return {"decision": "STOP", "reason": "vertical_chain_incomplete", "detail": vertical.get("reason")}
        if live_wiring is None:
            return {
                "decision": "STOP",
                "reason": TERMINAL_OFFLINE,
                "issue": 216,
                "patch_scope_verified": True,
                "publisher_handoff_ready": vertical.get("publisher_handoff_ready"),
                "model_invoked": False,
                "github_write": False,
                "publish_authorized": False,
            }
    if live_wiring is None:
        return {"decision": "STOP", "reason": "live_wiring_not_integrated"}
    if live_wiring.get("reason") != TERMINAL_WIRED:
        return {"decision": "STOP", "reason": "live_wiring_incomplete", "detail": live_wiring.get("reason")}
    return {
        "decision": "STOP",
        "reason": TERMINAL_WIRED,
        "issue": 216,
        "patch_scope_verified": True,
        "publisher_handoff_ready": live_wiring.get("publisher_handoff_ready"),
        "live_wiring_verified": True,
        "model_invoked": False,
        "github_write": False,
        "publish_authorized": False,
    }


def self_test():
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
        store = MemoryGitRef()
        vertical = run_offline_vertical(
            VerticalRequest(216, "777001", inventory, trusted=trusted_bundle(store), budget=BUDGET_OK),
            lease_store=store,
            workspace=root,
            base_sha=sha,
            apply_agent_change=lambda ws, _: target.write_text(
                "Supported Node 22 and 24; Node 26 forward smoke is not minimum support.\n",
                encoding="utf-8",
            ),
        )
        wired = integration_gate(216, inventory, patch, admission, vertical=vertical)
        assert wired["reason"] == TERMINAL_OFFLINE
        assert wired["publisher_handoff_ready"]
        from openhands_164_live_wiring import ProtectedWorkflowContext, APPROVED_OPERATION, CONTROL_ACTOR, CONTROL_REPO
        live_store = MemoryGitRef()
        live = run_protected_live_wiring(
            LiveWiringRequest(
                216, "777002", inventory,
                trusted=trusted_bundle(live_store), budget=BUDGET_OK,
                protected=ProtectedWorkflowContext(
                    CONTROL_REPO, CONTROL_ACTOR, "refs/heads/main", "workflow_dispatch",
                    "1", APPROVED_OPERATION, 216,
                ),
            ),
            lease_store=live_store,
            workspace=root,
            base_sha=sha,
            apply_agent_change=lambda ws, _: target.write_text(
                "Supported Node 22 and 24; Node 26 forward smoke is not minimum support.\n",
                encoding="utf-8",
            ),
        )
        finish = integration_gate(216, inventory, patch, admission, vertical=vertical, live_wiring=live)
        assert finish["reason"] == TERMINAL_WIRED
        assert finish["live_wiring_verified"]
        assert integration_gate(217, inventory, patch, admission)["reason"] == "unexpected_issue"
        assert integration_gate(216, inventory, {**patch, "base_sha": "b" * 40}, admission)["reason"] == "base_sha_mismatch"
        assert integration_gate(216, inventory, {**patch, "target": ALLOWED[217]}, admission)["reason"] == "patch_scope_unverified"
        assert integration_gate(216, inventory, patch, {"decision": "GO", "model_credential_handoff": True})["reason"] == "admission_not_fail_closed"
        assert integration_gate(216, inventory, patch, {"decision": "STOP", "model_credential_handoff": False, "openhands_authorized": False, "reason": "arbitrary"})["reason"] == "admission_not_fail_closed"
        assert integration_gate(216, {**inventory, "issues": []}, patch, admission)["reason"] == "queue_mismatch"
        print(json.dumps({"test": "issue216_integration_contract", "decision": "PASS",
                          "vertical_offline": TERMINAL_OFFLINE,
                          "live_admission": "BLOCKED", "model_invoked": False,
                          "github_write": False}, sort_keys=True))


if __name__ == "__main__":
    self_test()