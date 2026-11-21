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



SMOKE_WORKFLOW = "ai-eng-scheduled-hello-smoke.yml"


def collect_scheduled_smoke(fetch):
    """Read-only scheduled-run evidence; never equate a manual run with schedule."""
    url = BASE + "/actions/workflows/" + SMOKE_WORKFLOW + "/runs?event=schedule&per_page=10"
    try:
        payload = fetch(url)
        runs = payload.get("workflow_runs", [])
        if not isinstance(runs, list):
            raise ValueError("invalid_runs")
        matching = [run for run in runs if isinstance(run, dict)
                    and run.get("event") == "schedule"
                    and run.get("path", "").endswith(SMOKE_WORKFLOW)]
        if not matching:
            return {"decision": "UNKNOWN", "reason": "no_confirmed_scheduled_run"}
        latest = max(matching, key=lambda run: run.get("created_at") or "")
        result = {"run_id": latest.get("id"), "event": "schedule",
                  "created_at": latest.get("created_at"),
                  "started_at": latest.get("run_started_at"),
                  "status": latest.get("status"),
                  "conclusion": latest.get("conclusion"),
                  "head_sha": latest.get("head_sha"),
                  "url": latest.get("html_url")}
        result["decision"] = ("PASS" if result["status"] == "completed"
                              and result["conclusion"] == "success" else
                              "FAIL" if result["status"] == "completed" else "PENDING")
        return result
    except (urllib.error.URLError, TimeoutError, ValueError, TypeError,
            KeyError, OSError, AttributeError):
        return {"decision": "UNKNOWN", "reason": "github_evidence_unavailable"}

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
    scheduled = {"workflow_runs": [
        {"id": 10, "event": "workflow_dispatch", "path": ".github/workflows/" + SMOKE_WORKFLOW,
         "status": "completed", "conclusion": "success", "created_at": "2026-11-21T12:00:00Z"},
        {"id": 11, "event": "schedule", "path": ".github/workflows/" + SMOKE_WORKFLOW,
         "status": "completed", "conclusion": "success", "created_at": "2026-11-21T13:05:00Z"}]}
    assert collect_scheduled_smoke(lambda url: scheduled)["run_id"] == 11
    assert collect_scheduled_smoke(lambda url: scheduled)["decision"] == "PASS"
    assert collect_scheduled_smoke(lambda url: {"workflow_runs": []})["decision"] == "UNKNOWN"
    assert collect_scheduled_smoke(lambda url: {"workflow_runs": [
        scheduled["workflow_runs"][0]]})["decision"] == "UNKNOWN"
    assert collect_scheduled_smoke(lambda url: {"workflow_runs": [
        {**scheduled["workflow_runs"][1], "conclusion": "failure"}]})["decision"] == "FAIL"
    print("PASS: read-only snapshot and scheduled smoke fixtures; UNKNOWN remains UNKNOWN")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--scheduled-smoke", action="store_true")
    args = parser.parse_args()
    if sum((args.self_test, args.live, args.scheduled_smoke)) != 1:
        parser.error("choose exactly one mode")
    if args.self_test:
        self_test()
        return 0
    if args.scheduled_smoke:
        print(json.dumps(collect_scheduled_smoke(github_get), sort_keys=True))
        return 0
    snapshot = collect(github_get)
    print(json.dumps({"snapshot": snapshot, "plan": plan(snapshot)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
