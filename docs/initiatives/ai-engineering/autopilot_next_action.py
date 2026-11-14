#!/usr/bin/env python3
"""Deterministic, offline next-action planner. No network, agent, or write operations.

Input: JSON snapshot produced by a separate trusted collector.
Output: one actionable decision. A PASS never authorizes live execution.
"""
import argparse
import json
import sys

REQUIRED = ("ci", "scope", "lease", "writer", "budget", "owner_go",
            "executor", "open_pr_collision", "active_agent")
STATES = {"pass", "fail", "unknown"}
GATE_ORDER = ("ci", "scope", "open_pr_collision", "executor", "lease",
              "writer", "budget", "owner_go")
ACTIONS = {
    "ci": "repair_ci",
    "scope": "repair_scope",
    "open_pr_collision": "resolve_collision",
    "executor": "implement_executor",
    "lease": "verify_lease",
    "writer": "verify_writer",
    "budget": "verify_budget",
    "owner_go": "request_owner_approval",
}


def plan(snapshot):
    if not isinstance(snapshot, dict) or set(snapshot) != set(REQUIRED):
        return {"decision": "STOP", "reason": "invalid_or_incomplete_snapshot"}
    if any(value not in STATES for value in snapshot.values()):
        return {"decision": "STOP", "reason": "invalid_state"}
    if snapshot["active_agent"] != "fail":
        return {"decision": "STOP", "reason": "active_agent_or_unknown"}
    for gate in GATE_ORDER:
        if snapshot[gate] != "pass":
            return {"decision": "NEXT", "action": ACTIONS[gate],
                    "gate": gate, "state": snapshot[gate],
                    "live_execution_authorized": False}
    return {"decision": "STOP", "reason": "all_gates_reported_pass_but_no_execution_authority",
            "live_execution_authorized": False}


def self_test():
    base = dict.fromkeys(REQUIRED, "pass")
    base["active_agent"] = "fail"
    assert plan(base)["reason"] == "all_gates_reported_pass_but_no_execution_authority"
    assert plan({**base, "active_agent": "unknown"})["reason"] == "active_agent_or_unknown"
    assert plan({**base, "active_agent": "pass"})["reason"] == "active_agent_or_unknown"
    assert plan({**base, "ci": "fail"})["action"] == "repair_ci"
    assert plan({**base, "executor": "unknown"})["action"] == "implement_executor"
    assert plan({**base, "lease": "unknown"})["action"] == "verify_lease"
    assert plan({**base, "owner_go": "unknown"})["action"] == "request_owner_approval"
    assert plan({**base, "budget": "fail", "ci": "fail"})["action"] == "repair_ci"
    assert plan({**base, "budget": "maybe"})["reason"] == "invalid_state"
    assert plan({**base, "unexpected": "pass"})["reason"] == "invalid_or_incomplete_snapshot"
    print("PASS: offline next-action planner fixtures; no autonomous execution")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--snapshot")
    args = parser.parse_args()
    if args.self_test and not args.snapshot:
        self_test()
        return 0
    if not args.snapshot or args.self_test:
        parser.error("choose --self-test or --snapshot FILE")
    try:
        with open(args.snapshot, encoding="utf-8") as source:
            snapshot = json.load(source)
        result = plan(snapshot)
    except (OSError, ValueError, TypeError):
        result = {"decision": "STOP", "reason": "snapshot_unavailable"}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["decision"] == "NEXT" else 1


if __name__ == "__main__":
    sys.exit(main())
