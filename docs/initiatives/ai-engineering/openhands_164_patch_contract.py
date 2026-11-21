#!/usr/bin/env python3
"""#164: verify exactly one approved Haversine documentation change.

Pure local verifier. No model, GitHub API, credentials, lease mutation, or publishing.
This is a necessary artifact gate, never authorization to publish a PR.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ALLOWED = {
    216: "docs/compatibility.md",
    217: "docs/examples/v2-consumers.md",
    226: "docs/examples/v2-coding-assistants.md",
}
SHA = re.compile(r"[0-9a-f]{40}\Z")


class PatchContractError(ValueError):
    pass


def _git(root: pathlib.Path, *args: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True, capture_output=True, timeout=15,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise PatchContractError("git_evidence_unavailable") from exc


def verify_workspace_change(workspace: str | pathlib.Path, base_sha: str, issue: int) -> dict:
    if type(issue) is not int or issue not in ALLOWED:
        raise PatchContractError("issue_out_of_scope")
    if not isinstance(base_sha, str) or not SHA.fullmatch(base_sha):
        raise PatchContractError("invalid_base_sha")
    root = pathlib.Path(workspace).resolve(strict=True)
    if not root.is_dir() or not (root / ".git").exists():
        raise PatchContractError("not_git_checkout")
    if pathlib.Path(_git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve() != root:
        raise PatchContractError("workspace_not_repository_root")
    if _git(root, "rev-parse", "HEAD").decode().strip() != base_sha:
        raise PatchContractError("base_head_mismatch")
    target = ALLOWED[issue]
    status = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    entries = [entry for entry in status.split(b"\0") if entry]
    if len(entries) != 1 or len(entries[0]) < 4:
        raise PatchContractError("unexpected_changed_paths")
    entry = entries[0]
    if entry[:2] not in (b" M", b"M ", b"??"):
        raise PatchContractError("unsupported_change_kind")
    try:
        changed = entry[3:].decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise PatchContractError("invalid_changed_path") from exc
    if changed != target:
        raise PatchContractError("unexpected_changed_paths")
    file = root / target
    if file.is_symlink() or not file.is_file():
        raise PatchContractError("target_not_regular_file")
    if not file.read_bytes().strip():
        raise PatchContractError("empty_target")
    # No submodule, binary, rename, or secondary edits may be smuggled in.
    if b"\0" in file.read_bytes():
        raise PatchContractError("binary_target")
    return {"decision": "PATCH_SCOPE_VERIFIED", "issue": issue,
            "target": target, "base_sha": base_sha,
            "publish_authorized": False}



def prepare_verified_patch(workspace: str | pathlib.Path, base_sha: str,
                           issue: int, destination: str | pathlib.Path) -> dict:
    """Produce a review artifact, not a GitHub publication capability."""
    verdict = verify_workspace_change(workspace, base_sha, issue)
    root = pathlib.Path(workspace).resolve(strict=True)
    output = pathlib.Path(destination).resolve()
    if output == root or root in output.parents:
        raise PatchContractError("patch_must_be_outside_checkout")
    target = verdict["target"]
    tracked = _git(root, "ls-files", "--error-unmatch", "--", target)
    if tracked:
        patch = _git(root, "diff", "--binary", base_sha, "--", target)
    else:
        raise PatchContractError("target_tracking_unverified")
    if not patch or b"diff --git a/" + target.encode() + b" b/" + target.encode() not in patch:
        raise PatchContractError("patch_not_generated")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(patch)
    return {**verdict, "patch_created": True}


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        _git(root, "init", "-q")
        _git(root, "-c", "user.name=Test", "-c",
             "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "base")
        base = _git(root, "rev-parse", "HEAD").decode().strip()
        for issue, target in ALLOWED.items():
            path = root / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("grounded documentation change\n", encoding="utf-8")
            assert verify_workspace_change(root, base, issue)["decision"] == "PATCH_SCOPE_VERIFIED"
            try:
                verify_workspace_change(root, base, next(i for i in ALLOWED if i != issue))
            except PatchContractError as exc:
                assert str(exc) == "unexpected_changed_paths"
            else:
                raise AssertionError("wrong issue target accepted")
            path.unlink()
        for invalid in (0, 220, True):
            try:
                verify_workspace_change(root, base, invalid)
            except PatchContractError as exc:
                assert str(exc) == "issue_out_of_scope"
            else:
                raise AssertionError("invalid issue accepted")
    print("PASS: #164 single-file documentation patch scope (offline)")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    else:
        raise SystemExit("Usage: --self-test")
