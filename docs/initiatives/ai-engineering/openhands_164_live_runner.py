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

from github_ref_lease import GitHubRefStore, fingerprint
from openhands_164_budget_attestation import gates_only_budget_attestation
from openhands_164_ci_evidence import exact_head_ci_from_check_runs, pr_number_from_url
from openhands_164_executor import MODEL_DEFAULT
from openhands_164_issue_preflight import early_readonly_satisfaction_pinned
from openhands_164_sequential_handoff import SatisfiedIssueProof
from openhands_164_lease_session import ManagedLeaseSession
from openhands_164_live_wiring import (
    APPROVED_OPERATION,
    TERMINAL_CI_VERIFIED,
    TERMINAL_PUBLISHED,
    LiveExecutionConfig,
    LiveWiringRequest,
    build_trusted_workflow_attestation,
    protected_context_from_env,
    run_protected_live_wiring,
)
from openhands_164_production_gates import verify_isolated_g3_evidence, verify_provider_hard_cap, isolated_ruleset_evidence
from openhands_live_orchestrator import inspect as inventory_inspect
from openhands_lease_admission_adapter import request_id_for
from openhands_runner_admission_bridge import ProviderBudgetAttestation

HAVERSINE = "DaniilSydorenko/haversine-geolocation"
TARGET_REPO = HAVERSINE
EXACT_HEAD_CI_PENDING = "exact_head_ci_pending"
HQ_REPO = "DaniilSydorenko/.github"
_HANDOFF_RETAIN = frozenset({
    TERMINAL_PUBLISHED,
    TERMINAL_CI_VERIFIED,
    EXACT_HEAD_CI_PENDING,
    "ALREADY_SATISFIED",
})


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


def _require_lease_writer_token() -> tuple[str | None, dict | None]:
    token = os.environ.get("AI_ENG_LEASE_WRITER_TOKEN") or os.environ.get("AI_ENG_LEASE_TOKEN")
    if not isinstance(token, str) or not token.strip():
        return None, {"decision": "STOP", "reason": "lease_writer_token_missing"}
    return token.strip(), None


def _canonical_github_remote(url: str) -> str:
    normalized = url.strip()
    if "github.com/" in normalized:
        suffix = normalized.split("github.com/", 1)[1]
        if suffix.endswith(".git"):
            suffix = suffix[:-4]
        return "https://github.com/" + suffix
    return normalized


def _validate_target_workspace(workspace: pathlib.Path, base_sha: str) -> None:
    remote = subprocess.check_output(
        ["git", "-C", str(workspace), "remote", "get-url", "origin"], text=True, timeout=10
    ).strip()
    expected = "https://github.com/" + TARGET_REPO
    if _canonical_github_remote(remote).rstrip("/") != expected:
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


def _augment_with_lease_cleanup(result: dict, cleanup) -> dict:
    if cleanup is None:
        return result
    payload = dict(result)
    payload["lease_cleanup"] = {
        "attempted": cleanup.attempted,
        "released": cleanup.released,
        "outcome": cleanup.outcome,
    }
    return payload


def _attach_lease_handoff(result: dict, session: ManagedLeaseSession | None) -> dict:
    if session is None:
        return result
    phase = session.current_phase()
    if phase is None:
        return result
    out = dict(result)
    out["lease_phase"] = phase
    if result.get("reason") == EXACT_HEAD_CI_PENDING:
        out["lease_handoff"] = "durable_until_owner_ci_and_release"
    return out


def _attach_exact_head_ci(result: dict, *, read_token: str) -> dict:
    pr_url = result.get("pr_url")
    if not isinstance(pr_url, str):
        return result
    pr_number = pr_number_from_url(pr_url)
    if pr_number is None:
        return {**result, "reason": "published_pr_url_unparseable", "ci_verified": False}
    ci, err = exact_head_ci_from_check_runs(pr_number, transport=_github_transport, token=read_token)
    if err is not None:
        return {**result, **err, "ci_verified": False, "pr_url": pr_url, "pilot_complete": False}
    if ci is None:
        return {**result, "reason": EXACT_HEAD_CI_PENDING, "ci_verified": False, "pilot_complete": False, "pr_url": pr_url}
    out = {**result, "ci_verified": ci.verified(), "ci_aggregate": ci.aggregate, "ci_security": ci.security}
    if not ci.verified():
        out["reason"] = EXACT_HEAD_CI_PENDING
        out["pilot_complete"] = False
        return out
    out["reason"] = TERMINAL_CI_VERIFIED
    out["pilot_complete"] = True
    return out


def _finalize_lease(session: ManagedLeaseSession, result: dict) -> tuple[dict, object | None]:
    if result.get("reason") in _HANDOFF_RETAIN and result.get("lease_phase") in ("VERIFYING", None):
        phase = session.current_phase()
        if phase == "VERIFYING" or result.get("reason") == "ALREADY_SATISFIED":
            return _attach_lease_handoff(result, session), None
    if result.get("lease_phase") in ("BLOCKED", "RUNNING"):
        cleanup = session.block_failed_run_if_owned()
        return _augment_with_lease_cleanup(result, cleanup), cleanup
    cleanup = session.release_reserved_if_still_owned()
    if cleanup.released is False and session.current_phase() not in ("IDLE", None):
        cleanup = session.block_failed_run_if_owned()
    return _augment_with_lease_cleanup(result, cleanup), cleanup


# One bounded recovery for the audited Run #8 pre-dispatch release.
RECOVERY_HEAD = "47670c33fe97b7f32aeb2e97bceb0b2947153478"
RECOVERY_REQUEST = "openhands-164-issue-217-recovery-8"


def recovery_request_id(store, issue: int) -> str:
    original = request_id_for(issue)
    snap = store.read()
    if (issue == 217 and snap.sha == RECOVERY_HEAD
            and snap.state["phase"] == "IDLE"
            and snap.state["revision"] == 5
            and fingerprint(original) in snap.state["consumed_request_hashes"]
            and fingerprint(RECOVERY_REQUEST) not in snap.state["consumed_request_hashes"]):
        return RECOVERY_REQUEST
    return original


def run_pilot(workspace: str | pathlib.Path, issue: int = 216, *, live_attested: bool) -> dict:
    protected = protected_context_from_env()
    if protected is None:
        return {"decision": "STOP", "reason": "protected_workflow_context_missing"}
    if protected.operation != APPROVED_OPERATION:
        return {"decision": "STOP", "reason": "wrong_operation"}

    root = pathlib.Path(workspace).resolve(strict=True)

    read_token = os.environ.get("GH_TOKEN", "") or os.environ.get("GITHUB_TOKEN", "")
    if not read_token:
        return {"decision": "STOP", "reason": "github_read_token_missing"}

    try:
        inventory = inventory_inspect(
            lambda path: _github_transport("GET", f"https://api.github.com/repos/{HAVERSINE}{path}", read_token)
        )
    except Exception as exc:
        return {"decision": "STOP", "reason": "inventory_failed", "detail": type(exc).__name__}

    if inventory.get("reason") != "live_authorization_not_integrated":
        return {"decision": "STOP", "reason": "inventory_not_verified", "detail": inventory.get("reason")}

    base_sha = inventory["default_head"]

    if not live_attested:
        pinned = early_readonly_satisfaction_pinned(
            root, issue, pinned_base_sha=base_sha, workspace_validator=_validate_target_workspace,
        )
        if pinned is not None:
            if pinned.get("reason") == "ALREADY_SATISFIED":
                return {**pinned, "decision": "STOP", "model_invoked": False, "github_write": False}
            return pinned

    if live_attested:
        denied = verify_isolated_g3_evidence(issue)
        if denied is not None:
            return denied

    prior_proofs = ()
    if live_attested and issue == 217:
        pinned = early_readonly_satisfaction_pinned(
            root, 216, pinned_base_sha=base_sha, workspace_validator=_validate_target_workspace,
        )
        if not pinned or pinned.get("reason") != "ALREADY_SATISFIED":
            return {"decision": "STOP", "reason": "prior_issue216_satisfaction_unverified"}
        prior_proofs = (SatisfiedIssueProof(216, pinned["target"], base_sha),)

    lease_token, lease_err = _require_lease_writer_token()
    if lease_err is not None:
        return lease_err

    if live_attested:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        budget, budget_stop, _probe_evidence = verify_provider_hard_cap(api_key)
        if budget_stop is not None:
            return budget_stop
    else:
        budget = gates_only_budget_attestation()

    publish_token = os.environ.get("HAVERSINE_PUBLISH_TOKEN", "")

    lease_store = GitHubRefStore(HQ_REPO, lease_token)
    rid = recovery_request_id(lease_store, issue) if live_attested else request_id_for(issue)
    issue_url = f"https://github.com/{HAVERSINE}/issues/{issue}"
    session = ManagedLeaseSession(lease_store, rid, issue_url)
    acquire_outcome = session.acquire()
    if acquire_outcome not in (("ACQUIRED",) if live_attested else ("ACQUIRED", "ALREADY_OWNED")):
        return {"decision": "STOP", "reason": "lease_contention", "lease_outcome": acquire_outcome}

    if live_attested and session.current_phase() != "RESERVED":
        return {"decision": "STOP", "reason": "lease_not_reserved"}

    result: dict = {"decision": "STOP", "reason": "pilot_aborted"}
    try:
        try:
            _validate_target_workspace(root, base_sha)
        except PermissionError as exc:
            result = {"decision": "STOP", "reason": str(exc)}
        else:
            ruleset = isolated_ruleset_evidence(issue) if live_attested else None
            trusted = build_trusted_workflow_attestation(lease_store, issue, base_sha, ruleset=ruleset, rechecked_head_sha=base_sha)
            run_id = os.environ.get("GITHUB_RUN_ID", "0")
            open_prs: list[int] = []
            branch = f"ai-eng/issue-{issue}-openhands-164"
            try:
                existing = _github_transport(
                    "GET",
                    f"https://api.github.com/repos/{HAVERSINE}/pulls?state=open&head=DaniilSydorenko:{branch}",
                    read_token,
                )
                if isinstance(existing, list) and existing:
                    open_prs = [existing[0].get("number", 0)]
            except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
                result = {"decision": "STOP", "reason": "collision_query_failed"}
            else:
                live = LiveExecutionConfig(
                    live_attested=live_attested and os.environ.get("AI_ENG_LIVE_164_EXECUTE") == "1",
                    api_key=os.environ.get("OPENROUTER_API_KEY", "") if live_attested else None,
                    model=MODEL_DEFAULT,
                    publisher_token=publish_token if live_attested else None,
                )
                if live.live_attested and not publish_token:
                    result = {"decision": "STOP", "reason": "live_publisher_token_missing"}
                else:
                    result = run_protected_live_wiring(
                        LiveWiringRequest(
                            issue,
                            run_id,
                            inventory,
                            trusted=trusted,
                            prior_proofs=prior_proofs,
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
                        revalidate_target=lambda: _validate_target_workspace(root, base_sha),
                    )
                    if result.get("reason") == TERMINAL_PUBLISHED:
                        result = _attach_exact_head_ci(result, read_token=read_token)
                    elif result.get("reason") == TERMINAL_CI_VERIFIED:
                        result = {**result, "ci_verified": True, "pilot_complete": True}
    except Exception as exc:
        result = {"decision": "STOP", "reason": "pilot_exception", "detail": type(exc).__name__}
    finally:
        result, _ = _finalize_lease(session, result)
    return result


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
            sys.exit(0 if result.get("pilot_complete") is True or result.get("reason") == "ALREADY_SATISFIED" else 1)
        except Exception as error:
            print(json.dumps({"decision": "STOP", "reason": type(error).__name__}))
            sys.exit(1)
    elif len(sys.argv) >= 2 and sys.argv[1] == "--gates-only":
        workspace = sys.argv[2] if len(sys.argv) > 2 else "."
        issue = int(sys.argv[3]) if len(sys.argv) > 3 else 216
        result = run_pilot(workspace, issue=issue, live_attested=False)
        print(json.dumps(result, sort_keys=True))
        ok = result.get("reason") in ("ALREADY_SATISFIED", "live_164_vertical_wiring_verified_owner_gated")
        sys.exit(0 if ok and not result.get("model_invoked") and not result.get("github_write") else 1)
    else:
        sys.exit("Usage: --self-test | --gates-only WORKSPACE [ISSUE] | --live WORKSPACE [ISSUE]")