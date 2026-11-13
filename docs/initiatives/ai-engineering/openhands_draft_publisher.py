#!/usr/bin/env python3
"""Issue #220 GitHub Draft PR publisher.

No CLI or automatic entrypoint. Caller must provide a trusted authority object
from an independently protected workflow. The module never issues it.
"""
import json
import pathlib
import urllib.error
import urllib.request

from openhands_draft_handoff import BRANCH, ISSUE, REPO, TARGET


def request_json(method, url, token, payload=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url, data=body, method=method,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def publish_verified_proof(*, token, base_sha, proof_path, authority,
                           transport=request_json):
    if authority is not _PROTECTED_AUTHORITY:
        raise PermissionError("protected workflow authority missing")
    if len(base_sha) != 40 or any(c not in "0123456789abcdef" for c in base_sha):
        raise ValueError("invalid base SHA")
    path = pathlib.Path(proof_path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("invalid proof")
    from openhands_artifact_verifier import verify
    content = path.read_text(encoding="utf-8")
    if not verify([TARGET], content).startswith("PASS:"):
        raise ValueError("proof verification failed")

    api = "https://api.github.com/repos/" + REPO
    # Re-check base HEAD immediately before publishing; stale snapshots STOP.
    head = transport("GET", api + "/git/ref/heads/master", token)
    if head["object"]["sha"] != base_sha:
        raise RuntimeError("base moved; stop")
    existing = transport("GET", api + "/pulls?state=open&head=DaniilSydorenko:" + BRANCH, token)
    if existing:
        raise RuntimeError("branch PR already exists")
    # GitHub REST create-ref is atomic: existing branch rejects the request.
    transport("POST", api + "/git/refs", token,
              {"ref": "refs/heads/" + BRANCH, "sha": base_sha})
    import base64
    transport("PUT", api + "/contents/" + TARGET, token,
              {"message": "docs: OpenHands Issue #220 proof",
               "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
               "branch": BRANCH})
    return transport("POST", api + "/pulls", token,
                     {"title": "docs: OpenHands Issue #220 proof",
                      "head": BRANCH, "base": "master", "draft": True,
                      "body": "Closes no issues. OpenHands pilot for #" + str(ISSUE) +
                              ". Human review required; no auto-merge."})


# Not exposed via CLI; protected workflow authorization integration pending.
_PROTECTED_AUTHORITY = object()


def self_test():
    good = "OpenHands Issue #220: distance(a,b). This does not change behavior."
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        proof = pathlib.Path(temp) / "proof.md"
        proof.write_text(good, encoding="utf-8")
        calls = []
        def fake(method, url, token, payload=None):
            calls.append((method, url, payload))
            if "/git/ref/heads/master" in url:
                return {"object": {"sha": "a" * 40}}
            if "/pulls?" in url:
                return []
            return {"html_url": "https://example.invalid/draft"}
        try:
            publish_verified_proof(token="dummy", base_sha="a" * 40,
                                   proof_path=proof, authority=None, transport=fake)
        except PermissionError:
            pass
        else:
            raise AssertionError("untrusted publisher call accepted")
        assert calls == [], "unauthorized request was sent"
        result = publish_verified_proof(token="dummy", base_sha="a" * 40,
                                        proof_path=proof, authority=_PROTECTED_AUTHORITY,
                                        transport=fake)
        assert result["html_url"].endswith("/draft")
        assert [c[0] for c in calls] == ["GET", "GET", "POST", "PUT", "POST"]
        assert calls[-1][2]["draft"] is True
        calls.clear()
        def stale(method, url, token, payload=None):
            calls.append(method)
            return {"object": {"sha": "b" * 40}}
        try:
            publish_verified_proof(token="dummy", base_sha="a" * 40,
                                   proof_path=proof, authority=_PROTECTED_AUTHORITY,
                                   transport=stale)
        except RuntimeError:
            pass
        else:
            raise AssertionError("stale base accepted")
        assert calls == ["GET"]
    print("PASS: publisher mocked Draft PR lifecycle, unauthorized and stale rejection")


if __name__ == "__main__":
    self_test()
