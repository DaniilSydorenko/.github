#!/usr/bin/env python3
"""One-shot, owner-approved Haversine #220 execution; never publishes to GitHub.

Only invoke from the protected workflow. The owner/environment/concurrency
boundary lives in GitHub Actions, NOT in this Python process. The OpenRouter
key has its own provider-side $1 TOTAL limit. Output is a locally verified
patch artifact, not a PR or a success claim about publishing.
"""
import json
import os
import pathlib
import subprocess
import sys

from openrouter_budget_gate import probe
from openhands_issue_contract import live_preflight
from openhands_executor import execute_authorized, validate_workspace, _TRUSTED_AUTHORIZATION
from openhands_pipeline import handoff
from openhands_artifact_verifier import verify, changed_paths, TARGET

class ProofRejected(ValueError):
    """A stable verifier verdict, safe to print without exposing model output."""


MODEL = "openrouter/openai/gpt-4o-mini"
TARGET_REPO = "DaniilSydorenko/haversine-geolocation"


def gate(workspace, key, *, budget=probe, preflight=live_preflight):
    """Pure-ish admission checks; dependencies injected for offline tests."""
    if os.environ.get("GITHUB_REPOSITORY") != "DaniilSydorenko/.github":
        raise PermissionError("wrong_control_repository")
    if os.environ.get("GITHUB_ACTOR") != "DaniilSydorenko":
        raise PermissionError("wrong_actor")
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise PermissionError("wrong_control_ref")
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise PermissionError("not_manual_dispatch")
    if os.environ.get("AI_ENG_APPROVED_OPERATION") != "pilot-live-execute":
        raise PermissionError("wrong_operation")
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise PermissionError("rerun_disallowed")
    root = validate_workspace(workspace)
    remote = subprocess.check_output(
        ["git", "-C", str(root), "remote", "get-url", "origin"], text=True, timeout=10).strip()
    if remote not in (
        "https://github.com/" + TARGET_REPO,
        "https://github.com/" + TARGET_REPO + ".git",
    ):
        raise PermissionError("unexpected_target_remote")
    branch = subprocess.check_output(
        ["git", "-C", str(root), "symbolic-ref", "--short", "HEAD"],
        text=True, timeout=10).strip()
    if branch != "master":
        raise PermissionError("unexpected_target_branch")
    base = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, timeout=10).strip()
    if len(base) != 40 or any(c not in "0123456789abcdef" for c in base):
        raise PermissionError("invalid_base_sha")
    # Ensure checkout is at actual remote master, not a stale local clone.
    actual = subprocess.check_output(
        ["git", "-C", str(root), "ls-remote", "origin", "refs/heads/master"],
        text=True, timeout=20).split()
    if len(actual) != 2 or actual[0] != base:
        raise PermissionError("stale_target_base")
    scope = preflight()
    if scope.get("reason") != "scope_preflight_passed_but_live_gates_unverified":
        raise PermissionError("target_scope_not_clear")
    budget_verdict = budget(key)
    if budget_verdict.get("decision") != "PASS" or budget_verdict.get("reason") != "provider_key_limit_verified":
        raise PermissionError("provider_budget_not_verified")
    return root, base


def run(workspace, patch, key, *, executor=execute_authorized,
        budget=probe, preflight=live_preflight):
    root, base = gate(workspace, key, budget=budget, preflight=preflight)
    # This sentinel is a local implementation detail, not a security boundary.
    # The protected workflow is the only supported caller; no writer token exists.
    state = executor(root, key, MODEL, authorization=_TRUSTED_AUTHORIZATION)
    terminal = getattr(state, "value", state)
    if not isinstance(terminal, str) or terminal.lower() not in ("finished", "completed", "success"):
        raise RuntimeError("agent_terminal_not_success")
    # Provide a safe, actionable contract verdict before the patch handoff.
    # The first real run completed its model call but wrote incomplete proof.
    previous = pathlib.Path.cwd()
    try:
        os.chdir(root)
        paths = changed_paths(base)
    finally:
        os.chdir(previous)
    proof = root / TARGET
    content = proof.read_text(encoding="utf-8") if proof.is_file() and not proof.is_symlink() else ""
    verdict = verify(paths, content)
    if not verdict.startswith("PASS:"):
        raise ProofRejected(verdict)
    result = handoff(root, base, patch)
    if result.get("reason") != "protected_publisher_not_connected":
        raise RuntimeError("unexpected_publisher")
    return {"decision": "PATCH_VERIFIED", "base_sha": base,
            "issue": 220, "model_invoked": True, "github_write": False}


def self_test():
    import tempfile
    import unittest.mock as mock
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / "target"
        root.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "master", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "remote", "add", "origin",
                        "https://github.com/" + TARGET_REPO + ".git"], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit",
                        "--allow-empty", "-qm", "base"], check=True)
        base = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                       text=True).strip()
        env = dict(GITHUB_REPOSITORY="DaniilSydorenko/.github",
                   GITHUB_ACTOR="DaniilSydorenko", GITHUB_REF="refs/heads/main",
                   GITHUB_EVENT_NAME="workflow_dispatch",
                   AI_ENG_APPROVED_OPERATION="pilot-live-execute",
                   GITHUB_RUN_ATTEMPT="1")
        ok = lambda: {"reason": "scope_preflight_passed_but_live_gates_unverified"}
        budget = lambda key: {"decision": "PASS", "reason": "provider_key_limit_verified"}
        original = subprocess.check_output
        def git_check(cmd, **kwargs):
            if "ls-remote" in cmd:
                return (base + "\trefs/heads/master\n")
            return original(cmd, **kwargs)
        with mock.patch.dict(os.environ, env, clear=True), mock.patch(
                "subprocess.check_output", side_effect=git_check):
            assert gate(root, "offline", budget=budget, preflight=ok)[1] == base
            for field in env:
                with mock.patch.dict(os.environ, {field: "invalid"}):
                    try:
                        gate(root, "offline", budget=budget, preflight=ok)
                    except PermissionError:
                        pass
                    else:
                        raise AssertionError("accepted wrong " + field)
            try:
                gate(root, "offline", budget=lambda k: {"decision": "STOP"}, preflight=ok)
            except PermissionError:
                pass
            else:
                raise AssertionError("accepted invalid budget")
            try:
                gate(root, "offline", budget=budget, preflight=lambda: {"reason": "existing_issue_pr"})
            except PermissionError:
                pass
            else:
                raise AssertionError("accepted overlapping PR")
            called = []
            def fake_executor(workspace, key, model, *, authorization):
                called.append((model, authorization is _TRUSTED_AUTHORIZATION))
                proof = workspace / "docs/agent-pilot-proof.md"
                proof.parent.mkdir(parents=True)
                proof.write_text("OpenHands Issue #220: distance(a,b). This does not change behavior.\n")
                return "finished"
            result = run(root, pathlib.Path(tmp) / "proof.patch", "offline",
                         executor=fake_executor, budget=budget, preflight=ok)
            assert result["decision"] == "PATCH_VERIFIED"
            assert called == [(MODEL, True)]
            assert (pathlib.Path(tmp) / "proof.patch").is_file()
    print("PASS: protected live runner offline admission, fail-closed gates and verified patch")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif len(sys.argv) == 4 and sys.argv[1] == "--live":
        try:
            result = run(sys.argv[2], sys.argv[3], os.environ.get("OPENROUTER_API_KEY", ""))
            print(json.dumps(result, sort_keys=True))
        except Exception as error:
            # Do not log exception details: SDK/provider errors can contain secrets.
            print(json.dumps({"decision": "STOP", "reason": (str(error) if isinstance(error, ProofRejected) else type(error).__name__),
                              "model_may_have_been_invoked": True}))
            sys.exit(1)
    else:
        sys.exit("Usage: --self-test or --live WORKSPACE PATCH_PATH")
