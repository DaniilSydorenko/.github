#!/usr/bin/env python3
"""Protected workflow entry for OpenHands #164 Issues #216–#226.

Only invoke from ai-eng-164-protected-pilot with owner GO. Holds the CAS lease
through model execution and Draft PR publication when live attestation is set.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

from github_ref_lease import Controller, GitHubRefStore
from openhands_164_executor import MODEL_DEFAULT
from openhands_164_live_wiring import (
    APPROVED_OPERATION,
    LiveExecutionConfig,
    LiveWiringRequest,
    build_trusted_workflow_attestation,
    protected_context_from_env,
    run_protected_live_wiring,
)
from openhands_164_vertical_integration import CiEvidence
from openhands_live_orchestrator import inspect as inventory_inspect
from openhands_lease_admission_adapter import request_id_for
from openrouter_budget_gate import probe as budget_probe
from openhands_runner_admission_bridge import ProviderBudgetAttestation

HAVERSINE = "DaniilSydorenko/haversine-geolocation"
TARGET_REPO = HAVERSINE


def _github_transport(method: str, url: str, token: str, payload=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _budget_attestation(key: str) -> ProviderBudgetAttestation:
    verdict = budget_probe(key)
    return ProviderBudgetAttestation(
        verified_within_shared_cap=verdict.get("decision") == "PASS",
        attestation_source="trusted_workflow_budget_probe",
    )


def _validate_target_workspace(workspace: pathlib.Path, base_sha: str) -> None:
    remote = subprocess.check_output(
        ["git", "-C", str(workspace), "remote", "get-url", "origin"], text=True, timeout=10
    ).strip()
    if remote not in (
        "https://github.com/" + TARGET_REPO,
        "https://github.com/" + TARGET_REPO + ".git",
    ):
        raise PermissionError("unexpected_target_remote")
    branch = subprocess.check_output(
        ["git", "-C", str(workspace), "symbolic-ref", "--short", "HEAD"],
        text=True,
        timeout=10,
    ).strip()
    if branch != "master":
        raise PermissionError("unexpected_target_branch")
    head = subprocess.check_output(
        ["git", "-C", str(workspace), "rev-parse", "HEAD"], text=True, timeout=10
    ).strip()
    if head != base_sha:
        raise PermissionError("workspace_base_mismatch")
    actual = subprocess.check_output(
        ["git", "-C", str(workspace), "ls-remote", "origin", "refs/heads/master"],
        text=True,
        timeout=20,
    ).split()
    if len(actual) != 2 or actual[0] != base_sha:
        raise PermissionError("stale_target_base")


def run_pilot(workspace: str | pathlib.Path, issue: int = 216, *, live_attested: bool) -> dict:
    protected = protected_context_from_env()
    if protected is None:
        return {"decision": "STOP", "reason": "protected_workflow_context_missing"}
    if protected.operation != APPROVED_OPERATION:
        return {"decision": "STOP", "reason": "wrong_operation"}

    read_token = os.environ.get("GH_TOKEN", "") or os.environ.get("GITHUB_TOKEN", "")
    if not read_token:
        return {"decision": "STOP", "reason": "github_read_token_missing"}

    try:
        inventory = inventory_inspect(lambda path: _github_transport("GET", f"https://api.github.com/repos/{HAVERSINE}{path}", read_token))
    except Exception as exc:
        return {"decision": "STOP", "reason": "inventory_failed", "detail": type(exc).__name__}

    if inventory.get("reason") != "live_authorization_not_integrated":
        return {"decision": "STOP", "reason": "inventory_not_verified", "detail": inventory.get("reason")}

    base_sha = inventory["default_head"]
    root = pathlib.Path(workspace).resolve(strict=True)

    lease_token = os.environ.get("AI_ENG_LEASE_TOKEN", "") or read_token
    lease_store = GitHubRefStore("DaniilSydorenko/.github", lease_token)
    rid = request_id_for(issue)
    issue_url = f"https://github.com/{HAVERSINE}/issues/{issue}"
    acquired = Controller(lease_store).acquire(rid, issue_url)
    if acquired not in ("ACQUIRED", "ALREADY_OWNED"):
        return {"decision": "STOP", "reason": "lease_contention", "lease_outcome": acquired}

    trusted = build_trusted_workflow_attestation(lease_store, issue, base_sha)
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    budget = _budget_attestation(api_key)
    publish_token = os.environ.get("HAVERSINE_PUBLISH_TOKEN", "")

    try:
        _validate_target_workspace(root, base_sha)
    except PermissionError as exc:
        return {"decision": "STOP", "reason": str(exc)}

    run_id = os.environ.get("GITHUB_RUN_ID", "0")
    open_prs = []
    # Branch-scoped pilot PR collision for this issue only.
    branch = f"ai-eng/issue-{issue}-openhands-164"
    existing = _github_transport(
        "GET",
        f"https://api.github.com/repos/{HAVERSINE}/pulls?state=open&head=DaniilSydorenko:{branch}",
        read_token,
    )
    if isinstance(existing, list) and existing:
        open_prs = [existing[0].get("number", 0)]

    live = LiveExecutionConfig(
        live_attested=live_attested and os.environ.get("AI_ENG_LIVE_164_EXECUTE") == "1",
        api_key=api_key if live_attested else None,
        model=MODEL_DEFAULT,
        publisher_token=publish_token if live_attested else None,
    )

    return run_protected_live_wiring(
        LiveWiringRequest(
            issue,
            run_id,
            inventory,
            trusted=trusted,
            budget=budget,
            protected=protected,
            open_prs_for_target=open_prs,
            ci_after_publish=None,
        ),
        lease_store=lease_store,
        workspace=root,
        base_sha=base_sha,
        wiring_mode="live_execute" if live_attested else "live_gates_only",
        live_config=live,
        publisher_transport=_github_transport if live_attested else None,
    )


def self_test() -> None:
    assert protected_context_from_env() is None
    missing = run_pilot(".", live_attested=False)
    assert missing["reason"] == "protected_workflow_context_missing"
    print("PASS: #164 live runner fail-closed without workflow context")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif len(sys.argv) >= 2 and sys.argv[1] == "--live":
        workspace = sys.argv[2] if len(sys.argv) > 2 else "."
        issue = int(sys.argv[3]) if len(sys.argv) > 3 else 216
        try:
            result = run_pilot(workspace, issue=issue, live_attested=True)
            print(json.dumps(result, sort_keys=True))
            sys.exit(0 if result.get("reason") in (
                "live_164_draft_pr_published_pending_ci",
                "live_164_pilot_complete_ci_verified",
                "ALREADY_SATISFIED",
            ) else 1)
        except Exception as error:
            print(json.dumps({"decision": "STOP", "reason": type(error).__name__}))
            sys.exit(1)
    elif len(sys.argv) >= 2 and sys.argv[1] == "--gates-only":
        workspace = sys.argv[2] if len(sys.argv) > 2 else "."
        issue = int(sys.argv[3]) if len(sys.argv) > 3 else 216
        result = run_pilot(workspace, issue=issue, live_attested=False)
        print(json.dumps(result, sort_keys=True))
        sys.exit(0 if result.get("live_execute_path") or result.get("reason") == "ALREADY_SATISFIED" else 1)
    else:
        sys.exit("Usage: --self-test | --gates-only WORKSPACE [ISSUE] | --live WORKSPACE [ISSUE]")