#!/usr/bin/env python3
"""#164: authenticated, read-only live-pilot inventory. NO execution or writes.

This is the first fail-closed integration slice, NOT a live orchestrator.
A protected workflow must supply authority, a durable exclusive lease,
replay state, shared provider budget, and exact-head PR verification before
any paid agent call or automatic transition is possible.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request

from openhands_three_issue_gate import QUEUE

REPO = "DaniilSydorenko/haversine-geolocation"
API = "https://api.github.com/repos/" + REPO
SHA = re.compile(r"[0-9a-f]{40}\\Z")
EXPECTED = ((216, "docs/compatibility.md"),
            (217, "docs/examples/v2-consumers.md"),
            (226, "docs/examples/v2-coding-assistants.md"))


class AdmissionStop(RuntimeError):
    pass


def github_get(path, token):
    if not token:
        raise AdmissionStop("github_read_token_missing")
    req = urllib.request.Request(API + path, method="GET", headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError):
        raise AdmissionStop("github_evidence_unavailable") from None


def inspect(fetch):
    """Fetch all queue issues and ALL open PR files; unknown => STOP.

    A pagination boundary is deliberately a STOP, not an assumption of no
    collisions. This function returns evidence only, never authorization.
    """
    if tuple(QUEUE) != EXPECTED:
        raise AdmissionStop("trusted_queue_changed")
    head = fetch("/git/ref/heads/master")
    sha = head.get("object", {}).get("sha") if isinstance(head, dict) else None
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise AdmissionStop("default_head_unverified")
    issues = []
    for number, path in EXPECTED:
        issue = fetch("/issues/" + str(number))
        if (not isinstance(issue, dict) or issue.get("number") != number
                or issue.get("state") != "open"
                or issue.get("pull_request") is not None
                or not isinstance(issue.get("body"), str)
                or path not in issue["body"]):
            raise AdmissionStop("issue_scope_or_state_mismatch_" + str(number))
        issues.append({"number": number, "target": path})
    prs = fetch("/pulls?state=open&per_page=100&page=1")
    if not isinstance(prs, list) or len(prs) >= 100:
        raise AdmissionStop("pr_inventory_incomplete")
    active = []
    for pr in prs:
        if not isinstance(pr, dict) or type(pr.get("number")) is not int:
            raise AdmissionStop("invalid_pr_inventory")
        number = pr["number"]
        files = fetch("/pulls/" + str(number) + "/files?per_page=100&page=1")
        if not isinstance(files, list) or len(files) >= 100:
            raise AdmissionStop("pr_file_inventory_incomplete")
        paths = [f.get("filename") for f in files if isinstance(f, dict)]
        if len(paths) != len(files) or any(not isinstance(p, str) for p in paths):
            raise AdmissionStop("invalid_pr_files")
        if set(paths).intersection(path for _, path in EXPECTED):
            raise AdmissionStop("active_pr_overlaps_pilot_scope_" + str(number))
        active.append(number)
    return {"decision": "STOP", "reason": "live_authorization_not_integrated",
            "default_head": sha, "issues": issues, "open_prs_checked": active,
            "model_invoked": False, "github_write": False}


def self_test():
    def fake(path):
        if path == "/git/ref/heads/master":
            return {"object": {"sha": "a" * 40}}
        if path.startswith("/issues/"):
            n = int(path.split("/")[-1])
            return {"number": n, "state": "open",
                    "body": next(p for i, p in EXPECTED if i == n)}
        if path == "/pulls?state=open&per_page=100&page=1":
            return [{"number": 224}]
        if path == "/pulls/224/files?per_page=100&page=1":
            return [{"filename": "docs/agent-pilot-proof.md"}]
        raise AssertionError(path)
    good = inspect(fake)
    assert good["decision"] == "STOP" and good["reason"] == "live_authorization_not_integrated"
    assert good["open_prs_checked"] == [224]
    def reject(path, replacement_path, value):
        return value if path == replacement_path else fake(path)
    for path, value, reason in (
        ("/issues/216", {"number": 216, "state": "closed",
                          "body": EXPECTED[0][1]}, "issue_scope_or_state_mismatch_216"),
        ("/pulls?state=open&per_page=100&page=1", [{}], "invalid_pr_inventory"),
        ("/pulls/224/files?per_page=100&page=1",
         [{"filename": EXPECTED[1][1]}], "active_pr_overlaps_pilot_scope_224"),
        ("/pulls?state=open&per_page=100&page=1",
         [{"number": n} for n in range(100)], "pr_inventory_incomplete"),
    ):
        try:
            inspect(lambda p: reject(p, path, value))
        except AdmissionStop as error:
            assert str(error) == reason, (reason, error)
        else:
            raise AssertionError("unsafe evidence accepted: " + reason)
    print("PASS: #164 authenticated inventory contract (offline; no network/writes/model)")


def main():
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return 0
    if sys.argv[1:] != ["--read-only"]:
        print("Usage: --self-test | --read-only", file=sys.stderr)
        return 2
    try:
        result = inspect(lambda path: github_get(path, os.environ.get("GH_TOKEN", "")))
    except AdmissionStop as error:
        result = {"decision": "STOP", "reason": str(error),
                  "model_invoked": False, "github_write": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["reason"] == "live_authorization_not_integrated" else 1


if __name__ == "__main__":
    sys.exit(main())
