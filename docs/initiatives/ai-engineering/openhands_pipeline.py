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
from openhands_executor import execute_authorized, validate_workspace


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



def run_agent_then_handoff(workspace, base_sha, patch_output, *,
                           api_key, model, executor_authority, publisher=None,
                           executor=execute_authorized):
    """Single controlled call chain; execution never begins without authority.

    Publisher remains separately protected and optional. No CLI exposes this.
    """
    root = validate_workspace(workspace)
    if not isinstance(base_sha, str) or len(base_sha) != 40 or any(
            ch not in "0123456789abcdef" for ch in base_sha):
        raise ValueError("invalid base SHA")
    current = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, timeout=15).strip()
    if current != base_sha:
        raise ValueError("checkout HEAD differs from approved base")
    status = executor(root, api_key, model, authorization=executor_authority)
    # Fail closed unless the executor reports a known successful terminal state.
    if str(status).lower() not in ("finished", "completed", "success"):
        raise RuntimeError("agent did not report verified completion")
    return handoff(root, base_sha, patch_output, publisher=publisher)


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
        (root / "package.json").unlink()
        proof.unlink()
        try:
            run_agent_then_handoff(root, base, patch, api_key="dummy", model="mock",
                                   executor_authority=None)
        except PermissionError:
            pass
        else:
            raise AssertionError("untrusted agent execution accepted")
        invoked = []
        def mock_executor(*args, **kwargs):
            invoked.append("agent")
            proof.write_text("OpenHands Issue #220 distance(a,b). This does not change behavior.\\n".replace("\\\\n", "\\n"))
            return "completed"
        result = run_agent_then_handoff(
            root, base, patch, api_key="dummy", model="mock",
            executor_authority="fixture",
            executor=mock_executor)
        assert invoked == ["agent"] and result["decision"] == "STOP"
        proof.unlink()
        published = []
        def failed_agent(*args, **kwargs):
            proof.write_text("OpenHands Issue #220 distance(a,b). This does not change behavior.\\n")
            return "failed"
        try:
            run_agent_then_handoff(
                root, base, patch, api_key="dummy", model="mock",
                executor_authority="fixture", executor=failed_agent,
                publisher=lambda *args: published.append("unsafe"))
        except RuntimeError:
            pass
        else:
            raise AssertionError("failed agent accepted")
        assert not published, "publisher invoked after agent failure"
        proof.unlink()
        def bad_agent(*args, **kwargs):
            proof.write_text("OpenHands Issue #220 distance(a,b). This does not change behavior.\\n")
            (root / "package.json").write_text("unsafe", encoding="utf-8")
            return "completed"
        try:
            run_agent_then_handoff(
                root, base, patch, api_key="dummy", model="mock",
                executor_authority="fixture", executor=bad_agent,
                publisher=lambda *args: published.append("unsafe"))
        except ValueError:
            pass
        else:
            raise AssertionError("out-of-scope agent accepted")
        assert not published, "publisher invoked after out-of-scope changes"
    print("PASS: replayable agent patch and guarded publisher handoff")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("no live execution CLI; use --self-test")
    self_test()
