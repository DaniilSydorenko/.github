#!/usr/bin/env python3
"""#164 parameterized OpenHands SDK executor for Issues #216, #217, #226.

Live execution requires a protected workflow and verified admission wiring.
No CLI path grants model authority. Issue #220 remains on openhands_executor.py.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile

from openhands_164_patch_contract import ALLOWED

MODEL_DEFAULT = "openrouter/openai/gpt-4o-mini"
TARGET_REPO = "DaniilSydorenko/haversine-geolocation"
SHA = re.compile(r"[0-9a-f]{40}\Z")

_TRUSTED_AUTHORIZATION = object()


def _prompt(issue: int) -> str:
    target = ALLOWED[issue]
    return (
        f"Work on GitHub issue #{issue} only. Read the repository and change ONLY "
        f"{target}. Ground the documentation in real source files listed in the issue "
        f"and repository AGENTS.md. Do not change library behavior or any other "
        f"tracked/untracked file. Do not commit, push, open PRs, install packages, "
        f"or access secrets. Stop after writing the single scoped documentation file."
    )


def validate_workspace(workspace: str | pathlib.Path, issue: int, *, base_sha: str | None = None):
    if type(issue) is not int or issue not in ALLOWED:
        raise ValueError("issue_out_of_scope")
    if base_sha is not None and (not isinstance(base_sha, str) or not SHA.fullmatch(base_sha)):
        raise ValueError("invalid_base_sha")
    root = pathlib.Path(workspace).resolve(strict=True)
    if not root.is_dir() or not (root / ".git").exists():
        raise ValueError("workspace must be an existing Git checkout")
    try:
        check = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        if pathlib.Path(check.stdout.strip()).resolve() != root:
            raise ValueError("workspace is not the Git root")
        head = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, timeout=10
        ).strip()
        if base_sha is not None and head != base_sha:
            raise ValueError("base_head_mismatch")
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        if status.stdout.strip():
            raise ValueError("workspace is not clean")
    except (subprocess.SubprocessError, OSError) as error:
        raise ValueError("Git workspace verification failed") from error
    return root


def build_sdk_conversation(root, api_key, model, issue: int):
    from openhands.sdk import LLM, Agent, Conversation, Tool
    from openhands.tools.file_editor import FileEditorTool
    from pydantic import SecretStr

    llm = LLM(
        model=model,
        api_key=SecretStr(api_key),
        base_url="https://openrouter.ai/api/v1",
        usage_id=f"issue{issue}",
    )
    agent = Agent(llm=llm, tools=[Tool(name=FileEditorTool.name)])
    return Conversation(agent=agent, workspace=str(root))


def execute_authorized(root, api_key, model, issue: int, *, authorization):
    if authorization is not _TRUSTED_AUTHORIZATION:
        raise PermissionError("trusted_live_wiring_and_budget_required")
    if issue not in ALLOWED:
        raise ValueError("issue_out_of_scope")
    conversation = build_sdk_conversation(root, api_key, model, issue)
    conversation.send_message(_prompt(issue))
    conversation.run()
    return conversation.state.execution_status


def sdk_construction_test(issue: int = 216) -> None:
    """Instantiate pinned SDK locally with a dummy key; never invoke the model."""
    with tempfile.TemporaryDirectory() as temp:
        root = pathlib.Path(temp)
        subprocess.run(["git", "init", "-q", str(root)], check=True, timeout=10)
        subprocess.run(
            ["git", "-C", str(root), "-c", "user.name=Test", "-c",
             "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "base"],
            check=True,
            timeout=10,
        )
        conversation = build_sdk_conversation(
            validate_workspace(root, issue), "offline-construction-test-only", MODEL_DEFAULT, issue
        )
        assert conversation is not None
    print(f"PASS: #164 OpenHands SDK conversation constructed for issue {issue} (no model)")


def self_test() -> None:
    for issue in ALLOWED:
        assert f"#{issue}" in _prompt(issue) and ALLOWED[issue] in _prompt(issue)
    try:
        execute_authorized(None, None, None, 216, authorization=None)
    except PermissionError:
        pass
    else:
        raise AssertionError("unauthorized execution accepted")
    with tempfile.TemporaryDirectory() as temp:
        root = pathlib.Path(temp)
        subprocess.run(["git", "init", "-q", str(root)], check=True, timeout=10)
        subprocess.run(
            ["git", "-C", str(root), "-c", "user.name=Test", "-c",
             "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "base"],
            check=True,
            timeout=10,
        )
        sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        assert validate_workspace(root, 216, base_sha=sha) == root.resolve()
        (root / "dirty.txt").write_text("x", encoding="utf-8")
        try:
            validate_workspace(root, 216, base_sha=sha)
        except ValueError as error:
            assert str(error) == "workspace is not clean"
        else:
            raise AssertionError("dirty workspace accepted")
    print("PASS: #164 executor scope, prompt, and unauthorized rejection (offline)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--sdk-construction-test", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workspace")
    parser.add_argument("--issue", type=int, default=216)
    args = parser.parse_args()
    if args.sdk_construction_test and not (args.self_test or args.dry_run or args.workspace):
        if args.issue not in ALLOWED:
            print(json.dumps({"decision": "STOP", "reason": "issue_out_of_scope"}))
            return 1
        sdk_construction_test(args.issue)
        return 0
    if args.self_test and not args.dry_run and not args.workspace:
        self_test()
        return 0
    if args.dry_run and not args.self_test and args.workspace:
        try:
            root = validate_workspace(args.workspace, args.issue)
        except (OSError, ValueError) as error:
            print(json.dumps({"decision": "STOP", "reason": str(error)}))
            return 1
        if args.issue not in ALLOWED:
            print(json.dumps({"decision": "STOP", "reason": "issue_out_of_scope"}))
            return 1
        print(
            json.dumps(
                {
                    "decision": "STOP",
                    "reason": "live_164_wiring_integrated_owner_go_required",
                    "workspace": str(root),
                    "issue": args.issue,
                    "target": ALLOWED[args.issue],
                    "sdk_invocation": False,
                }
            )
        )
        return 0
    parser.error("choose --self-test or --dry-run --workspace PATH [--issue N]")
    return 2


if __name__ == "__main__":
    sys.exit(main())