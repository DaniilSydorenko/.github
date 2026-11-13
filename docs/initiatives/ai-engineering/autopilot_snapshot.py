#!/usr/bin/env python3
"""Read-only GitHub evidence collector for the Issue #220 next-action planner.

Unknown is never converted into PASS. Does not authorize execution.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

try:
    from autopilot_next_action import plan
    from openhands_issue_contract import live_preflight
except ImportError:
    from .autopilot_next_action import plan
    from .openhands_issue_contract import live_preflight

BASE = "https://api.github.com/repos/DaniilSydorenko/.github"
PR = 153


def collect(fetch):
    snapshot = {key: "unknown" for key in
                ("ci", "scope", "lease", "writer", "budget", "owner_go",
                 "executor", "open_pr_collision", "active_agent")}
    # Public GET evidence only. CI must match the exact current PR head.
    try:
        pr = fetch(BASE + "/pulls/" + str(PR))
        if not isinstance(pr, dict) or pr.get("state") != "open" or not pr.get("draft"):
            return snapshot
        sha = pr.get("head", {}).get("sha")
        if not isinstance(sha, str) or len(sha) != 40:
            return snapshot
        runs = fetch(BASE + "/actions/runs?head_sha=" + sha + "&per_page=100")
        matching = [r for r in runs.get("workflow_runs", [])
                    if r.get("head_sha") == sha and
                    r.get("name") == "AI Engineering OpenHands Runner Readiness (read-only)"]
        if matching:
            latest = max(matching, key=lambda r: r.get("run_number", 0))
            snapshot["ci"] = "pass" if latest.get("status") == "completed" and latest.get("conclusion") == "success" else "fail"
        # Static source evidence cannot prove live lease, budget, actor or executor.
        # Those gates deliberately remain UNKNOWN.
    except (urllib.error.URLError, TimeoutError, ValueError, TypeError, KeyError, OSError, AttributeError):
        return snapshot
    return snapshot


def github_get(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "ai-eng-autopilot-snapshot/1"}
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.load(response)


def self_test():
    sha = "a" * 40
    pr = {"state": "open", "draft": True, "head": {"sha": sha}}
    def good(url):
        if "/pulls/153" in url:
            return pr
        return {"workflow_runs": [{"head_sha": sha, "run_number": 3,
                 "name": "AI Engineering OpenHands Runner Readiness (read-only)",
                 "status": "completed", "conclusion": "success"}]}
    snapshot = collect(good)
    assert snapshot["ci"] == "pass"
    assert snapshot["lease"] == "unknown" and snapshot["executor"] == "unknown"
    assert plan(snapshot)["reason"] == "active_agent_or_unknown"
    assert collect(lambda url: {"state": "closed"})["ci"] == "unknown"
    def failed(url):
        if "/pulls/153" in url:
            return pr
        return {"workflow_runs": [{"head_sha": sha, "run_number": 4,
                 "name": "AI Engineering OpenHands Runner Readiness (read-only)",
                 "status": "completed", "conclusion": "failure"}]}
    assert collect(failed)["ci"] == "fail"
    print("PASS: read-only snapshot fixtures; UNKNOWN remains UNKNOWN")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.self_test == args.live:
        parser.error("choose exactly one mode")
    if args.self_test:
        self_test()
        return 0
    snapshot = collect(github_get)
    print(json.dumps({"snapshot": snapshot, "plan": plan(snapshot)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
