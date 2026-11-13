#!/usr/bin/env python3
"""Issue #220 post-agent handoff. No network or GitHub writes by default.

The trusted workflow must verify lease, budget and authorization separately.
"""
import argparse
import pathlib
import subprocess
import sys
import tempfile

from openhands_patch_prepare import prepare, TARGET
from openhands_draft_publisher import publish_verified_proof


def handoff(workspace, base_sha, patch_output, *, publisher=None):
    """Verify agent worktree, prepare replayable patch, optionally invoke injected publisher."""
    root = pathlib.Path(workspace).resolve(strict=True)
    patch = prepare(root, base_sha, patch_output)
    # Validate the patch against a fresh base checkout, not the agent worktree.
    with tempfile.TemporaryDirectory() as temp:
        replay = pathlib.Path(temp) / "replay"
        subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(root), str(replay)],
                       check=True, timeout=30)
        subprocess.run(["git", "-C", str(replay), "checkout", "-q", base_sha],
                       check=True, timeout=15)
        subprocess.run(["git", "-C", str(replay), "apply", "--check", str(patch)],
                       check=True, timeout=15)
        subprocess.run(["git", "-C", str(replay), "apply", str(patch)],
                       check=True, timeout=15)
        if (replay / TARGET).read_bytes() != (root / TARGET).read_bytes():
            raise ValueError("replayed proof mismatch")
    if publisher is None:
        return {"decision": "STOP", "reason": "protected_publisher_not_connected",
                "patch": str(patch)}
    return publisher(root / TARGET, base_sha)


def self_test():
    with tempfile.TemporaryDirectory() as temp:
        root = pathlib.Path(temp) / "repo"
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit",
                        "--allow-empty", "-qm", "base"], check=True)
        base = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                       text=True).strip()
        proof = root / TARGET
        proof.parent.mkdir(parents=True)
        proof.write_text("OpenHands Issue #220 distance(a,b). This does not change behavior.\n")
        patch = pathlib.Path(temp) / "artifact.patch"
        result = handoff(root, base, patch)
        assert result["decision"] == "STOP"
        assert result["reason"] == "protected_publisher_not_connected"
        assert patch.exists()
        called = []
        result = handoff(root, base, patch, publisher=lambda p, sha: called.append((p, sha)) or
                         {"decision": "MOCK_PUBLISHED"})
        assert result["decision"] == "MOCK_PUBLISHED" and len(called) == 1
        (root / "package.json").write_text("unexpected", encoding="utf-8")
        try:
            handoff(root, base, patch, publisher=lambda *_: called.append("unsafe"))
        except ValueError:
            pass
        else:
            raise AssertionError("extra changes accepted")
        assert len(called) == 1
    print("PASS: replayable agent patch and guarded publisher handoff")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("no live execution CLI; use --self-test")
    self_test()
