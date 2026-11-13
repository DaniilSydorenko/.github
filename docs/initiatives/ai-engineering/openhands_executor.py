#!/usr/bin/env python3
"""Issue #220 OpenHands SDK executor, currently dry-run only.

Live execution deliberately requires a separate trusted lease/authorization
integration; this module never accepts CLI flags as proof of authorization.
"""
import argparse
import json
import os
import pathlib
import sys

TARGET = "docs/agent-pilot-proof.md"
ISSUE = 220
PROMPT = (
    "Work on GitHub issue #220 only. Read the repository and create ONLY "
    + TARGET + ". Explain the distance(a, b) API with a short usage example. "
    "Do not change library behavior or any other tracked/untracked file. "
    "Do not commit, push, open PRs, install packages, or access secrets. "
    "Stop after writing the single documentation file."
)


def validate_workspace(workspace):
    root = pathlib.Path(workspace).resolve(strict=True)
    if not root.is_dir() or not (root / ".git").exists():
        raise ValueError("workspace must be an existing Git checkout")
    if (root / TARGET).exists():
        raise ValueError("target already exists")
    return root


def build_sdk_conversation(root, api_key, model):
    """Real OpenHands SDK wiring. Caller must provide verified execution authority."""
    from openhands.sdk import LLM, Agent, Conversation, Tool
    from openhands.tools.file_editor import FileEditorTool
    from openhands.tools.terminal import TerminalTool
    from pydantic import SecretStr

    llm = LLM(model=model, api_key=SecretStr(api_key),
              base_url="https://openrouter.ai/api/v1", usage_id="issue220")
    agent = Agent(llm=llm, tools=[
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
    ])
    return Conversation(agent=agent, workspace=str(root))


def execute_authorized(root, api_key, model, *, authorization):
    """Internal integration point: no user-controlled flag may satisfy this gate."""
    if authorization is not _TRUSTED_AUTHORIZATION:
        raise PermissionError("trusted lease and budget integration required")
    conversation = build_sdk_conversation(root, api_key, model)
    conversation.send_message(PROMPT)
    conversation.run()
    return conversation.state.execution_status


# Sentinel intentionally never issued by CLI or snapshot; integration pending.
_TRUSTED_AUTHORIZATION = object()


def self_test():
    assert "issue #220" in PROMPT and TARGET in PROMPT
    assert "Do not commit, push" in PROMPT
    try:
        execute_authorized(None, None, None, authorization=None)
    except PermissionError:
        pass
    else:
        raise AssertionError("unauthorized execution was accepted")
    print("PASS: OpenHands executor prompt and unauthorized execution rejection")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workspace")
    args = parser.parse_args()
    if args.self_test and not args.dry_run and not args.workspace:
        self_test()
        return 0
    if args.dry_run and not args.self_test and args.workspace:
        try:
            root = validate_workspace(args.workspace)
        except (OSError, ValueError) as error:
            print(json.dumps({"decision": "STOP", "reason": str(error)}))
            return 1
        print(json.dumps({"decision": "STOP", "reason": "live_authorization_not_integrated",
                          "workspace": str(root), "issue": ISSUE,
                          "target": TARGET, "sdk_invocation": False}))
        return 0
    parser.error("choose --self-test or --dry-run --workspace PATH")


if __name__ == "__main__":
    sys.exit(main())
