#!/usr/bin/env python3
"""#164 Draft PR publisher for Issues #216, #217, and #226.

No automatic CLI entrypoint. Caller must supply protected workflow authority.
Does not use the Issue #220 proof verifier or paths.
"""
from __future__ import annotations

import base64
import json
import pathlib

from openhands_164_patch_contract import ALLOWED

REPO = "DaniilSydorenko/haversine-geolocation"
_PROTECTED_AUTHORITY = object()


def branch_for(issue: int) -> str:
    if issue == 217:
        return "ai-eng/issue-217-openhands-164-correction-9"
    return f"ai-eng/issue-{issue}-openhands-164"


def publish_verified_patch(
    *,
    issue: int,
    token: str,
    base_sha: str,
    content_path: str | pathlib.Path,
    authority,
    transport,
):
    if authority is not _PROTECTED_AUTHORITY:
        raise PermissionError("protected_workflow_authority_missing")
    if type(issue) is not int or issue not in ALLOWED:
        raise ValueError("issue_out_of_scope")
    if len(base_sha) != 40 or any(c not in "0123456789abcdef" for c in base_sha):
        raise ValueError("invalid base SHA")
    target = ALLOWED[issue]
    path = pathlib.Path(content_path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 120_000:
        raise ValueError("invalid_content")
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError("empty_content")

    api = "https://api.github.com/repos/" + REPO
    head = transport("GET", api + "/git/ref/heads/master", token)
    if head["object"]["sha"] != base_sha:
        raise RuntimeError("base_moved_stop")
    branch = branch_for(issue)
    existing = transport(
        "GET", api + f"/pulls?state=all&head=DaniilSydorenko:{branch}", token
    )
    if existing:
        raise RuntimeError("branch_pr_already_exists")
    transport("POST", api + "/git/refs", token, {"ref": "refs/heads/" + branch, "sha": base_sha})
    existing_file = transport("GET", api + f"/contents/{target}?ref={branch}", token)
    payload = {
        "message": f"docs: OpenHands Issue #{issue} pilot documentation",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if isinstance(existing_file, dict) and isinstance(existing_file.get("sha"), str):
        payload["sha"] = existing_file["sha"]
    transport("PUT", api + "/contents/" + target, token, payload)
    return transport(
        "POST",
        api + "/pulls",
        token,
        {
            "title": f"docs: OpenHands Issue #{issue} pilot",
            "head": branch,
            "base": "master",
            "draft": True,
            "body": (
                f"Addresses #{issue}. Single-file documentation pilot via OpenHands #164 wiring. "
                "Human review required; no auto-merge."
            ),
        },
    )


def self_test() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as temp:
        doc = pathlib.Path(temp) / "doc.md"
        doc.write_text("Node compatibility documentation.\n", encoding="utf-8")
        calls: list[tuple] = []

        def fake(method, url, token, payload=None):
            calls.append((method, url, payload))
            if "/git/ref/heads/master" in url:
                return {"object": {"sha": "a" * 40}}
            if "/pulls?" in url:
                return []
            if "/contents/" in url and method == "GET":
                return {"message": "Not Found"}
            return {"html_url": "https://example.invalid/draft-216"}

        try:
            publish_verified_patch(
                issue=216,
                token="dummy",
                base_sha="a" * 40,
                content_path=doc,
                authority=None,
                transport=fake,
            )
        except PermissionError:
            pass
        else:
            raise AssertionError("untrusted publisher accepted")
        assert calls == []

        result = publish_verified_patch(
            issue=216,
            token="dummy",
            base_sha="a" * 40,
            content_path=doc,
            authority=_PROTECTED_AUTHORITY,
            transport=fake,
        )
        assert result["html_url"].endswith("draft-216")
        methods = [c[0] for c in calls]
        assert methods == ["GET", "GET", "POST", "GET", "PUT", "POST"]
        assert calls[-1][2]["draft"] is True
        assert branch_for(216) in calls[2][2]["ref"]

        calls.clear()

        def stale(method, url, token, payload=None):
            calls.append(method)
            return {"object": {"sha": "b" * 40}}

        try:
            publish_verified_patch(
                issue=217,
                token="x",
                base_sha="a" * 40,
                content_path=doc,
                authority=_PROTECTED_AUTHORITY,
                transport=stale,
            )
        except RuntimeError as error:
            assert str(error) == "base_moved_stop"
        else:
            raise AssertionError("stale base accepted")
        assert calls == ["GET"]

    print("PASS: #164 draft publisher mocked lifecycle, scope and stale rejection")


if __name__ == "__main__":
    self_test()