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
SHA = re.compile(r"[0-9a-f]{40}\Z")
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
    seen_pr_numbers = set()
    for pr in prs:
        if not isinstance(pr, dict) or type(pr.get("number")) is not int:
            raise AdmissionStop("invalid_pr_inventory")
        number = pr["number"]
        if number < 1 or number in seen_pr_numbers:
            raise AdmissionStop("duplicate_or_invalid_pr_number")
        seen_pr_numbers.add(number)
        # A PR may claim the issue without touching the target file yet.
        # Treat it as an existing writer, not as a free queue slot.
        body = pr.get("body")
        if body is not None and not isinstance(body, str):
            raise AdmissionStop("invalid_pr_body")
        if isinstance(body, str) and any(re.search(r"(?<![A-Za-z0-9_])#{}(?![0-9])".format(issue), body) for issue, _ in EXPECTED):
            raise AdmissionStop("active_pr_claims_pilot_issue_" + str(number))
        files = fetch("/pulls/" + str(number) + "/files?per_page=100&page=1")
        if not isinstance(files, list) or len(files) >= 100:
            raise AdmissionStop("pr_file_inventory_incomplete")
        paths = []
        for f in files:
            if not isinstance(f, dict) or not isinstance(f.get("filename"), str):
                raise AdmissionStop("invalid_pr_files")
            paths.append(f["filename"])
            # A rename FROM a pilot target also occupies that target.
            if f.get("status") == "renamed":
                previous = f.get("previous_filename")
                if not isinstance(previous, str) or not previous:
                    raise AdmissionStop("invalid_pr_rename")
                paths.append(previous)
        if set(paths).intersection(path for _, path in EXPECTED):
            raise AdmissionStop("active_pr_overlaps_pilot_scope_" + str(number))
        active.append(number)
    # Issues can close or be retargeted while the PR inventory is fetched.\n    # Require the same scoped, open issue evidence at the end of discovery.\n    for number, path in EXPECTED:\n        latest = fetch("/issues/" + str(number))\n        if (not isinstance(latest, dict) or latest.get("number") != number\n                or latest.get("state") != "open"\n                or latest.get("pull_request") is not None\n                or not isinstance(latest.get("body"), str)\n                or path not in latest["body"]):\n            raise AdmissionStop("issue_changed_during_inventory_" + str(number))\n    # Re-read the target base after the potentially long PR/issue inventory.
    # A moving base invalidates the snapshot; never return a coherent-looking
    # queue inventory assembled across two different master commits.
    final_head = fetch("/git/ref/heads/master")
    final_sha = (final_head.get("object", {}).get("sha")
                 if isinstance(final_head, dict) else None)
    if not isinstance(final_sha, str) or not SHA.fullmatch(final_sha):
        raise AdmissionStop("default_head_recheck_unverified")
    if final_sha != sha:
        raise AdmissionStop("default_head_changed_during_inventory")
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
        ("/pulls?state=open&per_page=100&page=1", [{"number": 224}, {"number": 224}], "duplicate_or_invalid_pr_number"),
        ("/pulls?state=open&per_page=100&page=1", [{"number": 224, "body": "Implements (#217), verified"}], "active_pr_claims_pilot_issue_224"),
        ("/pulls?state=open&per_page=100&page=1", [{"number": 224, "body": "Already addresses #216."}], "active_pr_claims_pilot_issue_224"),
        ("/pulls?state=open&per_page=100&page=1", [{"number": 224, "body": 7}], "invalid_pr_body"),
        ("/pulls/224/files?per_page=100&page=1",
         [{"filename": EXPECTED[1][1]}], "active_pr_overlaps_pilot_scope_224"),
        ("/pulls/224/files?per_page=100&page=1",
         [{"filename": "docs/other.md", "status": "renamed",
           "previous_filename": EXPECTED[0][1]}], "active_pr_overlaps_pilot_scope_224"),
        ("/pulls/224/files?per_page=100&page=1",
         [{"filename": "docs/other.md", "status": "renamed"}], "invalid_pr_rename"),
        ("/pulls?state=open&per_page=100&page=1",
         [{"number": n} for n in range(100)], "pr_inventory_incomplete"),
    ):
        try:
            inspect(lambda p: reject(p, path, value))
        except AdmissionStop as error:
            assert str(error) == reason, (reason, error)
        else:
            raise AssertionError("unsafe evidence accepted: " + reason)
    calls = [0]
    def moving_head(path):
        if path == "/git/ref/heads/master":
            calls[0] += 1
            if calls[0] == 2:
                return {"object": {"sha": "b" * 40}}
        return fake(path)
    try:
        inspect(moving_head)
    except AdmissionStop as error:
        assert str(error) == "default_head_changed_during_inventory"
    else:
        raise AssertionError("moving base accepted")
    calls[0] = 0
    def lost_head(path):
        if path == "/git/ref/heads/master":
            calls[0] += 1
            if calls[0] == 2:
                return {"object": {}}
        return fake(path)
    try:
        inspect(lost_head)
    except AdmissionStop as error:
        assert str(error) == "default_head_recheck_unverified"
    else:
        raise AssertionError("missing recheck accepted")
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
