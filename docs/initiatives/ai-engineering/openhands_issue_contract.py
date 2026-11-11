#!/usr/bin/env python3
"""Lane B: offline contract for Issue #220. NOT an OpenHands executor."""
import json
import sys

REPO = "DaniilSydorenko/haversine-geolocation"
ISSUE = 220
PATH = "docs/agent-pilot-proof.md"


def admit(issue, changed_paths, *, agent_active=False, lease_verified=False,
          writer_verified=False, budget_verified=False, owner_go=False):
    """Fail closed: content validation is necessary but not sufficient for launch."""
    if issue.get("number") != ISSUE or issue.get("state") != "open":
        return {"decision": "STOP", "reason": "wrong_issue"}
    body = issue.get("body") or ""
    if PATH not in body or "OpenHands" not in body:
        return {"decision": "STOP", "reason": "scope_missing"}
    if any(p != PATH for p in changed_paths) or len(changed_paths) != len(set(changed_paths)):
        return {"decision": "STOP", "reason": "out_of_scope_diff"}
    if agent_active:
        return {"decision": "STOP", "reason": "active_agent"}
    if not (lease_verified and writer_verified and budget_verified and owner_go):
        return {"decision": "STOP", "reason": "admission_not_proven"}
    return {"decision": "ADMISSION_CONDITIONS_MET", "reason": "not_an_execution_authorization"}


def self_test():
    issue = {"number": 220, "state": "open",
             "body": "OpenHands pilot; allowed docs/agent-pilot-proof.md"}
    assert admit(issue, [])["decision"] == "STOP"
    assert admit(issue, [PATH, "package.json"])["reason"] == "out_of_scope_diff"
    assert admit(issue, [PATH], agent_active=True)["reason"] == "active_agent"
    assert admit({**issue, "number": 219}, [PATH])["reason"] == "wrong_issue"
    assert admit(issue, [PATH], lease_verified=True, writer_verified=True,
                 budget_verified=True, owner_go=True)["decision"] == "ADMISSION_CONDITIONS_MET"
    print("PASS: Issue #220 fail-closed scope/admission contract; no agent launch")


if __name__ == "__main__":
    if sys.argv[1:] != ["--self-test"]:
        sys.exit("Only --self-test is supported; no live execution.")
    self_test()
