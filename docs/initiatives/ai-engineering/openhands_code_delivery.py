"""Bounded multi-file source delivery using one Git tree and one commit."""
from __future__ import annotations

import pathlib
import re
from openhands_164_patch_contract import _git, SHA, PatchContractError

SOURCE = re.compile(r"(?:src|tests?|fixtures)/[A-Za-z0-9_./-]+\.ts\Z")

def collect_changes(workspace, base_sha, allowed_paths):
    root = pathlib.Path(workspace).resolve(strict=True)
    allowed = frozenset(allowed_paths)
    if not SHA.fullmatch(base_sha) or not allowed or len(allowed) > 8:
        raise PatchContractError("invalid_task_scope")
    for name in allowed:
        if not SOURCE.fullmatch(name) or any(x in ("", ".", "..") for x in name.split("/")):
            raise PatchContractError("invalid_task_path")
    if _git(root, "rev-parse", "HEAD").decode().strip() != base_sha:
        raise PatchContractError("base_head_mismatch")
    changes = {}
    for entry in _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").split(b"\0"):
        if not entry:
            continue
        name = entry[3:].decode("utf-8")
        if entry[:2] not in (b" M", b"M ", b"??") or name not in allowed:
            raise PatchContractError("unexpected_changed_paths")
        path = root / name
        if path.resolve() != path or not path.is_file():
            raise PatchContractError("target_not_regular_file")
        data = path.read_bytes()
        if not data.strip() or b"\0" in data or len(data) > 120000:
            raise PatchContractError("invalid_content")
        changes[name] = data.decode("utf-8")
    if not changes or sum(len(x.encode()) for x in changes.values()) > 240000:
        raise PatchContractError("invalid_change_size")
    return changes

def publish_changes(*, issue, base_sha, changes, allowed_paths, token, authority, transport):
    from openhands_164_draft_publisher import REPO, _PROTECTED_AUTHORITY, branch_for
    if authority is not _PROTECTED_AUTHORITY:
        raise PermissionError("protected_workflow_authority_missing")
    if type(issue) is not int or issue <= 0 or not SHA.fullmatch(base_sha) or not changes or len(changes) > 8 or len(set(allowed_paths)) > 8 or not set(changes) <= set(allowed_paths):
        raise PatchContractError("invalid_publish_scope")
    for name, content in changes.items():
        if not SOURCE.fullmatch(name) or any(x in ("", ".", "..") for x in name.split("/")) or not content.strip() or "\0" in content or len(content.encode()) > 120000:
            raise PatchContractError("invalid_publish_content")
    if sum(len(x.encode()) for x in changes.values()) > 240000:
        raise PatchContractError("invalid_change_size")
    api = "https://api.github.com/repos/" + REPO
    branch = branch_for(issue)
    if transport("GET", api + "/git/ref/heads/master", token)["object"]["sha"] != base_sha:
        raise RuntimeError("base_moved_stop")
    if transport("GET", api + "/pulls?state=all&head=DaniilSydorenko:" + branch, token):
        raise RuntimeError("branch_pr_already_exists")
    base = transport("GET", api + "/git/commits/" + base_sha, token)
    tree = transport("POST", api + "/git/trees", token, {"base_tree": base["tree"]["sha"], "tree": [
        {"path": name, "mode": "100644", "type": "blob", "content": content}
        for name, content in sorted(changes.items())]})
    commit = transport("POST", api + "/git/commits", token, {"message": f"fix: address issue #{issue}", "tree": tree["sha"], "parents": [base_sha]})
    if transport("GET", api + "/git/ref/heads/master", token)["object"]["sha"] != base_sha:
        raise RuntimeError("base_moved_stop")
    transport("POST", api + "/git/refs", token, {"ref": "refs/heads/" + branch, "sha": commit["sha"]})
    return transport("POST", api + "/pulls", token, {"title": f"fix: address issue #{issue}", "head": branch, "base": "master", "draft": True, "body": f"Addresses #{issue}. Human review required."})
