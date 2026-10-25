"""Owner-only, strictly read-only GitHub IssueOps intake for Stage 2.

Runs on GitHub Actions' trusted default-branch checkout. Parses one owner
comment as untrusted data, verifies scoped repository/Issue/PR via GitHub GETs,
and emits REVIEW_ONLY or STOP. NEVER calls Cursor, acquires lease, signs a
launch permit, writes GitHub, changes billing or enqueues anything.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from trusted_github_evidence import LiveGitHub, GitHubHTTPError, SHA

MARKER = "AI_ENG_DISPATCH_REQUEST_V1\n"
CANONICAL_HQ = "DaniilSydorenko/.github"
CONTROL_ISSUE = 120
OWNER_LOGIN = "DaniilSydorenko"
ALLOWED = {CANONICAL_HQ, "DaniilSydorenko/listing-kit"}
ID = re.compile(r"[A-Za-z0-9_.:-]{8,128}\Z")


def _out(state: str, reason: str, *, ref: str | None = None) -> dict[str, Any]:
    return {"status": state, "reason": reason, "ref": ref,
            "launched": False, "cursor_api_called": False,
            "git_write": False, "owner_merge_authorized": False}


def parse_event(event: dict) -> dict:
    """Reject impersonation, PR comments, extra fields, shell syntax and scope."""
    if not isinstance(event, dict) or event.get("action") != "created":
        raise ValueError("unsupported event action")
    if event.get("repository", {}).get("full_name") != CANONICAL_HQ:
        raise ValueError("wrong control repository")
    issue, comment = event.get("issue"), event.get("comment")
    if not isinstance(issue, dict) or not isinstance(comment, dict):
        raise ValueError("missing Issue comment event")
    if type(issue.get("number")) is not int or issue["number"] != CONTROL_ISSUE:
        raise ValueError("not the owner-gated control Issue")
    if "pull_request" in issue:
        raise ValueError("pull request comments cannot trigger intake")
    if comment.get("user", {}).get("login") != OWNER_LOGIN:
        raise ValueError("comment author is not owner")
    if event.get("sender", {}).get("login") != OWNER_LOGIN:
        raise ValueError("event sender is not owner")
    if comment.get("author_association") not in ("OWNER", "MEMBER"):
        raise ValueError("unverified owner association")
    body = comment.get("body")
    if not isinstance(body, str) or len(body) > 2048 or not body.startswith(MARKER):
        raise ValueError("missing exact dispatch-request marker")
    raw = body[len(MARKER):]
    if not raw or raw.strip() != raw or "\n" in raw or "\r" in raw:
        raise ValueError("request must be one canonical JSON line")
    try:
        request = json.loads(raw)
    except ValueError as exc:
        raise ValueError("request JSON is invalid") from exc
    if not isinstance(request, dict) or set(request) != {
        "request_id", "repository", "issue_number", "pr_number", "head_sha",
    }:
        raise ValueError("request fields not exactly allowlisted")
    if (not isinstance(request["request_id"], str)
            or not ID.fullmatch(request["request_id"])
            or request["repository"] not in ALLOWED
            or type(request["issue_number"]) is not int or request["issue_number"] <= 0
            or type(request["pr_number"]) is not int or request["pr_number"] <= 0
            or not isinstance(request["head_sha"], str)
            or not SHA.fullmatch(request["head_sha"])):
        raise ValueError("malformed or out-of-scope request")
    return request


def verify_request_readonly(request: dict, api: Any) -> dict:
    """A verified metadata snapshot, not semantic PR or billing authorization."""
    owner, name = request["repository"].split("/", 1)
    issue_no, pr_no = request["issue_number"], request["pr_number"]
    base = f"/repos/{owner}/{name}"
    ref = f"https://github.com/{owner}/{name}/pull/{pr_no}"
    try:
        meta = api.get_json(base)
        branch = meta.get("default_branch")
        if not isinstance(branch, str) or not branch:
            return _out("STOP", "default_branch_unknown", ref=ref)
        first = api.get_json(base + f"/git/ref/heads/{branch}")
        head0 = first.get("object", {}).get("sha")
        if not isinstance(head0, str) or not SHA.fullmatch(head0):
            return _out("STOP", "default_sha_unknown", ref=ref)
        issue = api.get_json(base + f"/issues/{issue_no}")
        pull = api.get_json(base + f"/pulls/{pr_no}")
        again = api.get_json(base + f"/pulls/{pr_no}")
        final = api.get_json(base + f"/git/ref/heads/{branch}")
        head1 = final.get("object", {}).get("sha")
    except (GitHubHTTPError, KeyError, TypeError, ValueError):
        return _out("STOP", "github_read_unavailable_or_ambiguous", ref=ref)
    if (head0 != head1 or not isinstance(head1, str) or not SHA.fullmatch(head1)):
        return _out("STOP", "default_moved_during_check", ref=ref)
    if (issue.get("number") != issue_no or issue.get("state") != "open"
            or pull.get("number") != pr_no or again.get("number") != pr_no):
        return _out("STOP", "issue_or_pr_identity_invalid", ref=ref)
    first_head, second_head = pull.get("head", {}), again.get("head", {})
    first_base, second_base = pull.get("base", {}), again.get("base", {})
    if (pull.get("state") != "open" or again.get("state") != "open"
            or pull.get("draft") is not False or again.get("draft") is not False
            or first_head.get("sha") != request["head_sha"]
            or first_head.get("sha") != second_head.get("sha")
            or not isinstance(first_base.get("sha"), str)
            or not SHA.fullmatch(first_base["sha"])
            or first_base.get("sha") != second_base.get("sha")):
        return _out("STOP", "pr_closed_draft_stale_or_base_changed", ref=ref)
    return _out("REVIEW_ONLY", "metadata_current_but_owner_and_semantic_gates_unverified",
                ref=ref)


def process_event(event: dict, api: Any) -> dict:
    try:
        payload = parse_event(event)
    except (ValueError, TypeError, AttributeError, KeyError):
        return _out("STOP", "not_an_authenticated_owner_request")
    return verify_request_readonly(payload, api)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print(json.dumps(_out("STOP", "expected_github_event_path")))
        return 0
    try:
        event = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    except (ValueError, OSError):
        print(json.dumps(_out("STOP", "event_payload_unavailable")))
        return 0
    # Only create a network client after the strict owner/event check.
    try:
        request = parse_event(event)
    except (ValueError, TypeError, AttributeError, KeyError):
        print(json.dumps(_out("STOP", "not_an_authenticated_owner_request")))
        return 0
    import os
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print(json.dumps(_out("STOP", "no_readonly_github_token")))
        return 0
    report = verify_request_readonly(request, LiveGitHub(token))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
