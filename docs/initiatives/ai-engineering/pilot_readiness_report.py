#!/usr/bin/env python3
"""Read-only Haversine #220 pilot readiness report. Never launches agents."""
import argparse
import json

try:
    from openhands_issue_contract import live_preflight
except ImportError:
    from .openhands_issue_contract import live_preflight

BLOCKERS = (
    "trusted_live_executor_authorization_missing",
    "exclusive_lease_not_proven",
    "single_writer_not_proven",
    "model_budget_not_approved",
    "protected_publisher_not_live_proven",
    "automatic_next_issue_dispatch_not_implemented",
)


def report(preflight):
    """Do not mistake a scope preflight PASS for permission to execute."""
    if not isinstance(preflight, dict) or preflight.get("decision") != "STOP":
        return {"decision": "STOP", "reason": "invalid_preflight",
                "live_execution_authorized": False, "blockers": list(BLOCKERS)}
    reason = preflight.get("reason")
    if not isinstance(reason, str) or not reason:
        reason = "invalid_preflight"
    blockers = list(BLOCKERS)
    if reason != "scope_preflight_passed_but_live_gates_unverified":
        blockers.insert(0, "issue_scope_preflight_" + reason)
    return {"decision": "STOP", "reason": reason, "issue": 220,
            "live_execution_authorized": False, "blockers": blockers}


def self_test():
    ok = report({"decision": "STOP",
                 "reason": "scope_preflight_passed_but_live_gates_unverified"})
    assert ok["decision"] == "STOP" and not ok["live_execution_authorized"]
    assert len(ok["blockers"]) == len(BLOCKERS)
    collision = report({"decision": "STOP", "reason": "overlapping_pr_path"})
    assert collision["blockers"][0] == "issue_scope_preflight_overlapping_pr_path"
    for invalid in (None, {}, {"decision": "PASS"}, {"decision": "STOP"}):
        result = report(invalid)
        assert result["decision"] == "STOP" and not result["live_execution_authorized"]
    print("PASS: pilot readiness report is read-only and always fail-closed")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    result = report(live_preflight())
    print(json.dumps(result, sort_keys=True))
    # Diagnostic STOP is expected, not a successful launch.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
