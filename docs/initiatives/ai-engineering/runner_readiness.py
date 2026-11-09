#!/usr/bin/env python3
"""Read-only, fail-closed readiness probe for the first OpenHands issue pilot.

This is NOT an agent runner, lease, authorization, dispatcher, or paid-model launch.
Only public GitHub GETs. No credentials required and no mutation.
"""
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com/repos/DaniilSydorenko/haversine-geolocation"
ISSUES = (215, 216, 217)
ALLOWED = {
    215: "CONTRIBUTING.md",
    216: "docs/compatibility.md",
    217: "docs/examples/v2-consumers.md",
}


def get(path):
    request = urllib.request.Request(
        API + path,
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "openhands-readiness-probe-v1"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.load(response)


def inspect(fetch=get):
    """Advisory facts only. Unknown evidence => STOP, never implicit GO."""
    try:
        repo = fetch("")
        if repo.get("default_branch") != "master":
            return {"decision": "STOP", "reason": "unexpected_default_branch"}
        issues = [fetch("/issues/" + str(n)) for n in ISSUES]
        if any(x.get("pull_request") or x.get("state") != "open" for x in issues):
            return {"decision": "STOP", "reason": "issue_missing_or_not_open"}
        for n, issue in zip(ISSUES, issues):
            body = issue.get("body") or ""
            if ALLOWED[n] not in body:
                return {"decision": "STOP", "reason": "scope_not_confirmed", "issue": n}
        prs = fetch("/pulls?state=open&per_page=100")
        if not isinstance(prs, list) or len(prs) == 100:
            return {"decision": "STOP", "reason": "pr_inventory_incomplete"}
        overlapping = [
            {"number": p.get("number"), "head": (p.get("head") or {}).get("ref")}
            for p in prs
            if "#215" in (p.get("body") or "") or
               "#216" in (p.get("body") or "") or
               "#217" in (p.get("body") or "") or
               "pilot/215-" in ((p.get("head") or {}).get("ref") or "")
        ]
        return {
            "decision": "STOP",
            "reason": "live_runner_and_exclusive_lease_not_verified",
            "default_branch": "master",
            "issues_checked": list(ISSUES),
            "allowed_paths": ALLOWED,
            "matching_open_prs": overlapping,
            "agent_launched": False,
            "lease_verified": False,
            "budget_verified": False,
            "provider_cost": "UNKNOWN",
        }
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
        return {"decision": "STOP", "reason": "github_evidence_unavailable",
                "error_type": type(exc).__name__}


def self_test():
    def fixture(path):
        if path == "":
            return {"default_branch": "master"}
        if path.startswith("/issues/"):
            n = int(path.rsplit("/", 1)[-1])
            return {"state": "open", "body": "Allowed file: " + ALLOWED[n]}
        if path.startswith("/pulls?"):
            return [{"number": 219, "body": "Closes #215",
                     "head": {"ref": "pilot/215-fast-mvp-docs"}}]
        raise AssertionError(path)
    result = inspect(fixture)
    assert result["decision"] == "STOP"
    assert result["reason"] == "live_runner_and_exclusive_lease_not_verified"
    assert result["matching_open_prs"][0]["number"] == 219
    assert inspect(lambda path: {"default_branch": "main"})["decision"] == "STOP"
    assert inspect(lambda path: (_ for _ in ()).throw(ValueError()))["decision"] == "STOP"
    print("PASS: offline fail-closed fixtures")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif sys.argv[1:] == ["--live"]:
        print(json.dumps(inspect(), indent=2, sort_keys=True))
    else:
        print("Usage: runner_readiness.py --self-test|--live", file=sys.stderr)
        sys.exit(2)
