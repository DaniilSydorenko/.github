#!/usr/bin/env python3
"""Fail-closed, offline authorization boundary for Haversine OpenHands #220.

A report, snapshot, CLI argument or owner text is never execution authority.
This module deliberately has NO live grant factory or CLI launch path.
"""
from dataclasses import dataclass

REPO = "DaniilSydorenko/haversine-geolocation"
ISSUE = 220
PATH = "docs/agent-pilot-proof.md"
MAX_SPEND_USD = 1.00


@dataclass(frozen=True)
class Admission:
    repository: str
    issue: int
    path: str
    base_sha: str
    max_spend_usd: float


def check_admission(admission, *, lease, writer, owner, budget, executor,
                    no_collision, no_active_agent):
    """Return STOP or a non-authorizing verdict. Never grants an executor token."""
    if not isinstance(admission, Admission):
        return {"decision": "STOP", "reason": "untrusted_admission"}
    if admission.repository != REPO or admission.issue != ISSUE or admission.path != PATH:
        return {"decision": "STOP", "reason": "scope_mismatch"}
    if (not isinstance(admission.base_sha, str) or len(admission.base_sha) != 40 or
            any(c not in "0123456789abcdef" for c in admission.base_sha)):
        return {"decision": "STOP", "reason": "invalid_base_sha"}
    if (not isinstance(admission.max_spend_usd, (int, float)) or
            isinstance(admission.max_spend_usd, bool) or
            not 0 < admission.max_spend_usd <= MAX_SPEND_USD):
        return {"decision": "STOP", "reason": "invalid_budget_cap"}
    gates = {
        "lease": lease, "writer": writer, "owner": owner, "budget": budget,
        "executor": executor, "no_collision": no_collision,
        "no_active_agent": no_active_agent,
    }
    for gate, value in gates.items():
        # Only literal bool True accepted; truthy strings and numbers are rejected.
        if value is not True:
            return {"decision": "STOP", "reason": gate + "_not_verified"}
    return {"decision": "CONDITIONS_MET", "reason": "live_authority_still_required",
            "live_execution_authorized": False}


def self_test():
    base = Admission(REPO, ISSUE, PATH, "a" * 40, 0.50)
    gates = dict.fromkeys(("lease", "writer", "owner", "budget", "executor",
                           "no_collision", "no_active_agent"), True)
    verdict = check_admission(base, **gates)
    assert verdict["decision"] == "CONDITIONS_MET"
    assert verdict["live_execution_authorized"] is False
    for gate in gates:
        for invalid in (False, None, "pass", 1, {}, []):
            assert check_admission(base, **{**gates, gate: invalid})["decision"] == "STOP"
    assert check_admission(None, **gates)["reason"] == "untrusted_admission"
    assert check_admission(Admission(REPO, 221, PATH, "a" * 40, .5), **gates)["reason"] == "scope_mismatch"
    assert check_admission(Admission(REPO, ISSUE, PATH, "x" * 40, .5), **gates)["reason"] == "invalid_base_sha"
    for cap in (0, -1, 1.01, float("nan"), float("inf"), True, "1"):
        assert check_admission(Admission(REPO, ISSUE, PATH, "a" * 40, cap), **gates)["reason"] == "invalid_budget_cap"
    print("PASS: strict admission checks; no live execution authorization")


if __name__ == "__main__":
    self_test()
