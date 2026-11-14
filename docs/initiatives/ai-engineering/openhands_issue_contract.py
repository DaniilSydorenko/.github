#!/usr/bin/env python3
"""Lane B: offline contract for Issue #220. NOT an OpenHands executor."""
import sys
import json
import urllib.request
import urllib.error

REPO = "DaniilSydorenko/haversine-geolocation"
ISSUE = 220
PATH = "docs/agent-pilot-proof.md"


def admit(issue, changed_paths, *, agent_active=False, lease_verified=False,
          writer_verified=False, budget_verified=False, owner_go=False):
    """Fail closed: content validation is necessary but not sufficient for launch."""
    if issue.get("number") != ISSUE or issue.get("state") != "open":
        return {"decision": "STOP", "reason": "wrong_issue"}
    # GitHub issues and pull requests share the Issues API; never admit a PR.
    if "pull_request" in issue:
        return {"decision": "STOP", "reason": "not_an_issue"}
    if issue.get("repository_url") not in (None, "https://api.github.com/repos/" + REPO):
        return {"decision": "STOP", "reason": "wrong_repository"}
    body = issue.get("body") or ""
    if PATH not in body or "OpenHands" not in body:
        return {"decision": "STOP", "reason": "scope_missing"}
    if not changed_paths:
        return {"decision": "STOP", "reason": "no_changes"}
    if any(p != PATH for p in changed_paths) or len(changed_paths) != len(set(changed_paths)):
        return {"decision": "STOP", "reason": "out_of_scope_diff"}
    if agent_active:
        return {"decision": "STOP", "reason": "active_agent"}
    if not (lease_verified and writer_verified and budget_verified and owner_go):
        return {"decision": "STOP", "reason": "admission_not_proven"}
    return {"decision": "ADMISSION_CONDITIONS_MET", "reason": "not_an_execution_authorization"}


def live_preflight(fetch=None):
    """Public GET-only target evidence; never grants a launch or acquires a lease."""
    base = "https://api.github.com/repos/" + REPO
    def github_get(path):
        request = urllib.request.Request(base + path, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "openhands-issue220-preflight/1",
        }, method="GET")
        with urllib.request.urlopen(request, timeout=12) as response:
            return json.load(response)
    fetch = fetch or github_get
    try:
        repo = fetch("")
        issue = fetch("/issues/220")
        prs = fetch("/pulls?state=open&per_page=100")
        if repo.get("default_branch") != "master":
            return {"decision": "STOP", "reason": "unexpected_default_branch"}
        if not isinstance(prs, list) or len(prs) >= 100:
            return {"decision": "STOP", "reason": "pr_inventory_incomplete"}
        if any("#220" in (p.get("body") or "") for p in prs):
            return {"decision": "STOP", "reason": "existing_issue_pr"}
        # Check actual changed paths, not only descriptions.
        for pr in prs:
            number = pr.get("number")
            if not isinstance(number, int) or number < 1:
                return {"decision": "STOP", "reason": "invalid_pr_inventory"}
            files = fetch("/pulls/" + str(number) + "/files?per_page=100")
            if not isinstance(files, list) or len(files) >= 100:
                return {"decision": "STOP", "reason": "pr_file_inventory_incomplete"}
            if any(not isinstance(item, dict) or not isinstance(item.get("filename"), str)
                   for item in files):
                return {"decision": "STOP", "reason": "invalid_pr_files"}
            if any(item["filename"] == PATH or item.get("previous_filename") == PATH
                   for item in files):
                return {"decision": "STOP", "reason": "overlapping_pr_path"}
        file_present = True
        try:
            fetch("/contents/" + PATH + "?ref=master")
        except urllib.error.HTTPError as error:
            if error.code == 404:
                file_present = False
            else:
                raise
        if file_present:
            return {"decision": "STOP", "reason": "target_file_already_exists"}
        scope = admit(issue, [PATH])
        if scope["reason"] not in ("admission_not_proven",):
            return scope
        return {"decision": "STOP", "reason": "scope_preflight_passed_but_live_gates_unverified",
                "issue": ISSUE, "target_path_absent": True,
                "lease_verified": False, "writer_verified": False,
                "budget_verified": False, "owner_go_verified": False}
    except (urllib.error.URLError, TimeoutError, ValueError, TypeError, KeyError, OSError):
        return {"decision": "STOP", "reason": "github_evidence_unavailable"}


def preflight_self_test():
    issue = {"number": 220, "state": "open", "body": "OpenHands docs/agent-pilot-proof.md",
             "repository_url": "https://api.github.com/repos/" + REPO}
    def good(path):
        if path == "":
            return {"default_branch": "master"}
        if path == "/issues/220":
            return issue
        if path.startswith("/pulls?"):
            return []
        raise urllib.error.HTTPError(path, 404, "Not Found", {}, None)
    assert live_preflight(good)["reason"] == "scope_preflight_passed_but_live_gates_unverified"
    assert live_preflight(lambda p: [{"body": "#220"}] if p.startswith("/pulls?") else good(p))["reason"] == "existing_issue_pr"
    assert live_preflight(lambda p: {"sha": "exists"} if p.startswith("/contents/") else good(p))["reason"] == "target_file_already_exists"
    def overlap(path):
        if path.startswith("/pulls/1/files"):
            return [{"filename": PATH}]
        if path.startswith("/pulls?"):
            return [{"number": 1, "body": ""}]
        return good(path)
    assert live_preflight(overlap)["reason"] == "overlapping_pr_path"
    def incomplete(path):
        if path.startswith("/pulls/1/files"):
            return [{"filename": "docs/unrelated.md"}] * 100
        if path.startswith("/pulls?"):
            return [{"number": 1, "body": ""}]
        return good(path)
    assert live_preflight(incomplete)["reason"] == "pr_file_inventory_incomplete"
    print("PASS: Issue #220 read-only preflight fixtures (no network, no authorization)")

def self_test():
    issue = {"number": 220, "state": "open",
             "body": "OpenHands pilot; allowed docs/agent-pilot-proof.md"}
    assert admit(issue, [])["reason"] == "no_changes"
    assert admit(issue, [PATH, "package.json"])["reason"] == "out_of_scope_diff"
    assert admit(issue, [PATH, PATH])["reason"] == "out_of_scope_diff"
    assert admit({**issue, "body": "OpenHands pilot"}, [PATH])["reason"] == "scope_missing"
    assert admit(issue, [PATH], agent_active=True)["reason"] == "active_agent"
    assert admit({**issue, "number": 219}, [PATH])["reason"] == "wrong_issue"
    assert admit({**issue, "pull_request": {}}, [PATH])["reason"] == "not_an_issue"
    assert admit({**issue, "repository_url": "https://api.github.com/repos/other/repo"}, [PATH])["reason"] == "wrong_repository"
    assert admit(issue, [PATH], lease_verified=True, writer_verified=True,
                 budget_verified=True, owner_go=True)["decision"] == "ADMISSION_CONDITIONS_MET"
    preflight_self_test()
    print("PASS: Issue #220 fail-closed scope/admission contract; no agent launch")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif sys.argv[1:] == ["--live-preflight"]:
        result = live_preflight()
        print(json.dumps(result, sort_keys=True))
        sys.exit(0 if result["reason"] == "scope_preflight_passed_but_live_gates_unverified" else 1)
    else:
        sys.exit("Only --self-test or --live-preflight is supported; no agent execution.")
