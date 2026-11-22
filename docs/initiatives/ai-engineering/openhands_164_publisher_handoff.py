#!/usr/bin/env python3
"""#164: verify a scoped OpenHands patch against an exact clean checkout.

No model calls, GitHub writes, lease issuance, or publish authority.
"""
from __future__ import annotations

import pathlib
import subprocess
import tempfile

from openhands_164_patch_contract import ALLOWED, PatchContractError, _git, SHA


def verify_patch_for_handoff(checkout, base_sha, issue, patch_path):
    if type(issue) is not int or issue not in ALLOWED:
        raise PatchContractError("issue_out_of_scope")
    if not isinstance(base_sha, str) or not SHA.fullmatch(base_sha):
        raise PatchContractError("invalid_base_sha")
    root = pathlib.Path(checkout).resolve(strict=True)
    original_patch = pathlib.Path(patch_path)
    if original_patch.is_symlink():
        raise PatchContractError("invalid_patch")
    patch = original_patch.resolve(strict=True)
    if not patch.is_file() or patch.stat().st_size > 50000:
        raise PatchContractError("invalid_patch")
    if patch == root or root in patch.parents:
        raise PatchContractError("patch_inside_checkout")
    if _git(root, "rev-parse", "HEAD").decode().strip() != base_sha:
        raise PatchContractError("base_head_mismatch")
    if _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all"):
        raise PatchContractError("dirty_checkout")
    data = patch.read_bytes()
    target = ALLOWED[issue].encode()
    header = b"diff --git a/" + target + b" b/" + target + b"\n"
    if not data.startswith(header) or data.count(b"diff --git ") != 1:
        raise PatchContractError("unexpected_patch_scope")
    if (b"GIT binary patch" in data or b"Binary files " in data
            or bytes([0]) in data or bytes([13]) in data):
        raise PatchContractError("binary_patch_disallowed")
    try:
        subprocess.run(["git", "-C", str(root), "apply", "--check",
                        "--", str(patch)], capture_output=True, check=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        raise PatchContractError("patch_not_applicable") from exc
    return {"decision": "READY_FOR_PROTECTED_PUBLISHER_REVIEW",
            "issue": issue, "target": ALLOWED[issue],
            "base_sha": base_sha, "publish_authorized": False}


def self_test():
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)
        root = base / "repo"
        root.mkdir()
        _git(root, "init", "-q")
        _git(root, "-c", "user.name=Test", "-c",
             "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "base")
        sha = _git(root, "rev-parse", "HEAD").decode().strip()
        target = ALLOWED[216]
        patch = base / "test.patch"
        patch.write_text("diff --git a/" + target + " b/" + target +
                         "\nnew file mode 100644\nindex 0000000..f2376e2\n"
                         "--- /dev/null\n+++ b/" + target +
                         "\n@@ -0,0 +1 @@\n+verified docs\n", encoding="utf-8")
        assert verify_patch_for_handoff(root, sha, 216, patch)["publish_authorized"] is False
        for issue in (217, 226, 220):
            try:
                verify_patch_for_handoff(root, sha, issue, patch)
            except PatchContractError:
                pass
            else:
                raise AssertionError("cross-issue patch accepted")
        symlink = base / "symlink.patch"
        symlink.symlink_to(patch)
        try:
            verify_patch_for_handoff(root, sha, 216, symlink)
        except PatchContractError as exc:
            assert str(exc) == "invalid_patch"
        else:
            raise AssertionError("symlink patch accepted")
        symlink.unlink()
        original = patch.read_bytes()
        patch.write_bytes(original + bytes([0]))
        try:
            verify_patch_for_handoff(root, sha, 216, patch)
        except PatchContractError as exc:
            assert str(exc) == "binary_patch_disallowed"
        else:
            raise AssertionError("NUL payload accepted")
        patch.write_bytes(original)
        (root / "untracked").write_text("dirty")
        try:
            verify_patch_for_handoff(root, sha, 216, patch)
        except PatchContractError as exc:
            assert str(exc) == "dirty_checkout"
        else:
            raise AssertionError("dirty checkout accepted")
    print("PASS: offline #164 patch-to-publisher handoff contract")


if __name__ == "__main__":
    self_test()
