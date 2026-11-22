#!/usr/bin/env python3
"""Fail-closed cross-component publisher boundary test for Issue 216.

No network, model, lease acquisition or GitHub write. The legacy #220
publisher is intentionally NOT an authorization path for #216.
"""
from __future__ import annotations
import json
from issue216_integration_contract import integration_gate
from openhands_164_sequential_handoff import next_issue
from openhands_live_orchestrator import EXPECTED
from openhands_164_patch_contract import ALLOWED
from openhands_runner_admission_bridge import evaluate_before_model_handoff
from openhands_draft_publisher import publish_verified_proof

def run():
    sha = "a" * 40
    inventory = {"reason": "live_authorization_not_integrated", "default_head": sha,
                 "issues": [{"number": n, "target": p} for n, p in EXPECTED]}
    patch = {"decision": "PATCH_SCOPE_VERIFIED", "target": ALLOWED[216], "base_sha": sha}
    admission = evaluate_before_model_handoff(
        216, "integration-test", trusted_attestation=None, budget_attestation=None)
    verdict = integration_gate(216, inventory, patch, admission)
    assert verdict["decision"] == "STOP"
    assert verdict["reason"] == "protected_lease_and_publisher_not_integrated"
    assert verdict["model_invoked"] is False and verdict["github_write"] is False
    queue = next_issue([])
    assert queue["next_issue"] == 216 and queue["dispatch_authorized"] is False
    requests = []
    def forbidden_transport(*args, **kwargs):
        requests.append((args, kwargs))
        raise AssertionError("unauthorized GitHub network request")
    try:
        publish_verified_proof(token="never-real", base_sha=sha,
                               proof_path="/nonexistent/issue216.md",
                               authority=None, transport=forbidden_transport)
    except PermissionError:
        pass
    else:
        raise AssertionError("legacy publisher accepted Issue 216")
    assert not requests
    print(json.dumps({"decision": "PASS", "issue": 216,
                      "integration": "fail_closed", "publisher": "blocked",
                      "next_issue": queue["next_issue"],
                      "model_invoked": False, "github_write": False}, sort_keys=True))

if __name__ == "__main__":
    run()
