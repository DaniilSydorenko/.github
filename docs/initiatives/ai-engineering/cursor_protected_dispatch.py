#!/usr/bin/env python3
"""Protected owner-triggered Cursor dispatch for Haversine Issue #220 only.

Composes issue preflight, public lease competing-writer observation,
singleton admission, managed_cursor_launch (activation OFF), and optional
cursor_readonly inventory. Never acquires a lease, alters lease state, or
POSTs to Cursor. Workflow-injected context is the only dispatch authority
surface; caller JSON flags are never trusted.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from cursor_pr_payload import PayloadError, single_issue_payload
from github_ref_lease import PREFIX, agent_id_for, check_state, fingerprint
from managed_cursor_launch import PILOT_ACTIVATION_ENABLED
from openhands_issue_contract import PATH, REPO, live_preflight
from openhands_live_admission import Admission, check_admission
from openhands_runner_admission_bridge import caller_json_carries_forbidden_attestation
from singleton_admission import evaluate as singleton_evaluate

ISSUE = 220
LEASE_REPO = "DaniilSydorenko/.github"
LEASE_REF = "ai-eng-cursor-lease-v1"
LEASE_API = "https://api.github.com/repos/" + LEASE_REPO
CONTROL_REPO = "DaniilSydorenko/.github"
CONTROL_ACTOR = "DaniilSydorenko"
APPROVED_OPERATION = "pilot-cursor-220-dispatch-gates-only"
DEFAULT_MODEL = "composer-2"
MODEL_ALLOWLIST = frozenset({DEFAULT_MODEL})
SHA = re.compile(r"[0-9a-f]{40}\Z")


@dataclass(frozen=True)
class ProtectedCursorContext:
    """Workflow-injected dispatch context; never parse from issue text or inputs."""

    repository: str
    actor: str
    ref: str
    event_name: str
    run_attempt: str
    operation: str
    owner_go_issue: int
    workflow_run_id: str
    execute_cursor_requested: bool


def _stop(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "decision": "STOP",
        "reason": reason,
        "issue": ISSUE,
        "executor": "cursor",
        "live_cursor_dispatch_authorized": False,
        "cursor_post_attempted": False,
        "pilot_activation_enabled": PILOT_ACTIVATION_ENABLED is True,
        **extra,
    }


def protected_context_from_env() -> ProtectedCursorContext | None:
    repo = os.environ.get("GITHUB_REPOSITORY")
    actor = os.environ.get("GITHUB_ACTOR")
    ref = os.environ.get("GITHUB_REF")
    event = os.environ.get("GITHUB_EVENT_NAME")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
    operation = os.environ.get("AI_ENG_APPROVED_OPERATION")
    issue_raw = os.environ.get("AI_ENG_OWNER_GO_ISSUE")
    run_id = os.environ.get("GITHUB_RUN_ID")
    execute = os.environ.get("AI_ENG_EXECUTE_CURSOR", "").lower() in ("1", "true", "yes")
    if not all(isinstance(x, str) and x for x in (repo, actor, ref, event, attempt, run_id)):
        return None
    if operation != APPROVED_OPERATION:
        return None
    if issue_raw != str(ISSUE):
        return None
    if repo != CONTROL_REPO or actor != CONTROL_ACTOR or event != "workflow_dispatch":
        return None
    if ref != "refs/heads/main" or attempt != "1":
        return None
    return ProtectedCursorContext(
        repository=repo,
        actor=actor,
        ref=ref,
        event_name=event,
        run_attempt=attempt,
        operation=operation,
        owner_go_issue=ISSUE,
        workflow_run_id=run_id,
        execute_cursor_requested=execute,
    )


def validate_workflow_context(ctx: ProtectedCursorContext | None) -> dict[str, Any] | None:
    if ctx is None:
        return _stop("protected_workflow_context_missing_or_untrusted")
    if ctx.owner_go_issue != ISSUE:
        return _stop("owner_go_issue_not_220")
    if ctx.operation != APPROVED_OPERATION:
        return _stop("approved_operation_mismatch")
    return None


def parse_public_lease_state(commit_message: str) -> dict[str, Any]:
    if not isinstance(commit_message, str) or not commit_message.startswith(PREFIX):
        raise ValueError("lease_prefix_missing")
    payload = commit_message[len(PREFIX):]
    state = json.loads(payload)
    check_state(state)
    return state


def competing_writer_verdict(lease_state: dict[str, Any]) -> dict[str, Any]:
    phase = lease_state.get("phase")
    if phase != "IDLE":
        return {
            "competing_writer": True,
            "reason": "global_lease_not_idle",
            "lease_phase": phase,
            "lease_request_id": lease_state.get("request_id"),
            "lease_source_issue_url": lease_state.get("source_issue_url"),
            "lease_pr_url": lease_state.get("pr_url"),
        }
    return {"competing_writer": False, "reason": "lease_idle", "lease_phase": "IDLE"}


def request_id_for_dispatch(ctx: ProtectedCursorContext) -> str:
    return f"cursor-haversine-220-{ctx.workflow_run_id}"


def build_proposal(*, request_id: str, main_sha: str) -> dict[str, Any]:
    try:
        return single_issue_payload(
            request_id=request_id,
            repository=REPO,
            issue_number=ISSUE,
            exact_default_sha=main_sha,
            allowed_paths=[PATH],
            model_id=DEFAULT_MODEL,
            model_allowlist=MODEL_ALLOWLIST,
        )
    except PayloadError as exc:
        return _stop("cursor_payload_invalid", detail=str(exc))


def admission_gates_unmet(main_sha: str) -> dict[str, Any]:
    admission = Admission(REPO, ISSUE, PATH, main_sha, 1.0)
    return check_admission(
        admission,
        lease=False,
        writer=False,
        owner=False,
        budget=False,
        executor=False,
        no_collision=False,
        no_active_agent=False,
    )


def summarize_launch_attempt(
    launch: dict[str, Any], *, proposal: dict[str, Any] | None
) -> dict[str, Any]:
    state = launch.get("state")
    if state == "DISABLED":
        return _stop(
            "owner_activation_not_enabled",
            managed_launch_state=state,
            managed_launch_reason=launch.get("reason"),
            proposal_status=proposal.get("status") if isinstance(proposal, dict) else None,
            agent_id=proposal.get("payload", {}).get("agentId")
            if isinstance(proposal, dict)
            else None,
        )
    return _stop(
        "unexpected_managed_launch_state",
        managed_launch_state=state,
        managed_launch_reason=launch.get("reason"),
    )


def run_gates_only(
    ctx: ProtectedCursorContext,
    *,
    issue_preflight: Callable[[], dict[str, Any]],
    lease_state_reader: Callable[[], dict[str, Any]],
    main_sha_reader: Callable[[], str],
    caller_context: Mapping[str, Any] | None = None,
    cursor_inventory: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Owner-triggered audit path. Always fail-closed before any Cursor POST."""
    blocked = validate_workflow_context(ctx)
    if blocked is not None:
        return blocked
    forbidden = caller_json_carries_forbidden_attestation(caller_context or {})
    if forbidden:
        return _stop("caller_attestation_fields_not_trusted", forbidden_keys=sorted(forbidden))
    if ctx.execute_cursor_requested and PILOT_ACTIVATION_ENABLED is not True:
        # Explicit owner checkbox alone is never authority; activation stays OFF.
        pass
    try:
        lease_state = lease_state_reader()
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return _stop("lease_state_unreadable", error_type=type(exc).__name__)
    writer = competing_writer_verdict(lease_state)
    if writer["competing_writer"]:
        return _stop(
            writer["reason"],
            competing_writer=True,
            lease_phase=writer.get("lease_phase"),
            lease_request_id=writer.get("lease_request_id"),
            lease_source_issue_url=writer.get("lease_source_issue_url"),
            lease_pr_url=writer.get("lease_pr_url"),
        )
    preflight = issue_preflight()
    if not isinstance(preflight, dict):
        return _stop("issue_preflight_invalid")
    if preflight.get("reason") != "scope_preflight_passed_but_live_gates_unverified":
        return _stop(
            "issue_preflight_" + str(preflight.get("reason", "failed")),
            preflight_decision=preflight.get("decision"),
        )
    try:
        main_sha = main_sha_reader()
    except (ValueError, TypeError, KeyError) as exc:
        return _stop("default_branch_sha_unavailable", error_type=type(exc).__name__)
    if not isinstance(main_sha, str) or not SHA.fullmatch(main_sha):
        return _stop("invalid_default_branch_sha")
    admission = admission_gates_unmet(main_sha)
    if admission.get("live_execution_authorized") is True:
        return _stop("admission_boundary_leaked_authority")
    singleton = singleton_evaluate(
        {
            "evidence_complete": False,
            "budget_controls_verified": False,
            "cursor_on_demand_disabled": False,
            "external_billing_excluded": False,
            "model_allowlisted": False,
            "subagents_disabled": False,
            "launch_routes_exclusive": False,
            "request_id": request_id_for_dispatch(ctx),
            "prior_request_ids": [],
            "lease": {"verified_atomic": False, "state": "OWNED", "owner_request_id": "other"},
            "provider_run_inventory_complete": False,
            "ambiguous_previous_launch": True,
            "active_run_ids": ["run-active"] if cursor_inventory else [],
            "scope_authorized": False,
            "owner_sensitive": True,
            "attempt_number": 0,
            "semantic_reconciliation_accepted": False,
            "main_sha": main_sha,
            "observed_main_sha": main_sha,
            "open_prs": [],
            "intent": {"kind": "NEW_CODE", "issue_approved": False,
                       "dependency_evidence_complete": False,
                       "independent_leaf_proven": False, "no_overlap_verified": False},
        }
    )
    inventory_note: dict[str, Any] | None = None
    if cursor_inventory is not None:
        try:
            inventory_note = cursor_inventory()
        except Exception as exc:  # noqa: BLE001 — inventory is observational only
            inventory_note = {"status": "STOP", "reason": type(exc).__name__}
    rid = request_id_for_dispatch(ctx)
    proposal = build_proposal(request_id=rid, main_sha=main_sha)
    if proposal.get("decision") == "STOP":
        return proposal
    launch = {
        "state": "DISABLED" if PILOT_ACTIVATION_ENABLED is not True else "STOP",
        "reason": "owner_activation_not_enabled",
        "launched": False,
    }
    result = summarize_launch_attempt(launch, proposal=proposal)
    result.update(
        {
            "preflight_reason": preflight.get("reason"),
            "admission_reason": admission.get("reason"),
            "singleton_decision": singleton.get("decision"),
            "singleton_reason": singleton.get("reason"),
            "proposal_agent_id": agent_id_for(rid),
            "exact_head_verification": "pending_after_terminal_run",
        }
    )
    if inventory_note is not None:
        result["cursor_inventory"] = inventory_note
    return result


def _github_get(path: str) -> dict[str, Any]:
    request = urllib.request.Request(
        (LEASE_API if path.startswith("/git/") else f"https://api.github.com/repos/{REPO}") + path,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "cursor-protected-dispatch-gates/1",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        body = json.load(response)
    if not isinstance(body, dict):
        raise ValueError("github_response_not_object")
    return body


def live_lease_state() -> dict[str, Any]:
    ref = _github_get(f"/git/ref/heads/{LEASE_REF}")
    sha = ((ref.get("object") or {}).get("sha"))
    if not isinstance(sha, str):
        raise ValueError("lease_ref_missing")
    commit = _github_get("/git/commits/" + sha)
    return parse_public_lease_state(commit.get("message") or "")


def live_main_sha() -> str:
    repo = _github_get("")
    branch = repo.get("default_branch")
    if branch != "master":
        raise ValueError("unexpected_default_branch")
    ref = _github_get(f"/git/ref/heads/{branch}")
    sha = ((ref.get("object") or {}).get("sha"))
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise ValueError("invalid_master_sha")
    return sha


def run_live_gates_only() -> dict[str, Any]:
    ctx = protected_context_from_env()
    return run_gates_only(
        ctx,  # type: ignore[arg-type]
        issue_preflight=live_preflight,
        lease_state_reader=live_lease_state,
        main_sha_reader=live_main_sha,
    )


def self_test() -> None:
    idle = {"phase": "IDLE", "version": 1, "revision": 0, "request_id": None,
            "consumed_request_hashes": []}
    assert competing_writer_verdict(idle)["competing_writer"] is False
    rid = "cursor-test-request"
    busy = {
        **idle,
        "phase": "VERIFYING",
        "request_id": rid,
        "agent_id": "bc-00000000-0000-0000-0000-000000000000",
        "source_issue_url": "https://github.com/a/b/issues/1",
        "pr_url": "https://github.com/a/b/pull/1",
        "revision": 1,
        "consumed_request_hashes": [fingerprint(rid)],
        "run_id": "run-00000000-0000-0000-0000-000000000001",
    }
    check_state(busy)
    verdict = competing_writer_verdict(busy)
    assert verdict["competing_writer"] is True

    ctx = ProtectedCursorContext(
        repository=CONTROL_REPO,
        actor=CONTROL_ACTOR,
        ref="refs/heads/main",
        event_name="workflow_dispatch",
        run_attempt="1",
        operation=APPROVED_OPERATION,
        owner_go_issue=ISSUE,
        workflow_run_id="12345",
        execute_cursor_requested=False,
    )
    good_preflight = {"decision": "STOP",
                      "reason": "scope_preflight_passed_but_live_gates_unverified"}
    main = "a" * 40

    out = run_gates_only(
        ctx,
        issue_preflight=lambda: good_preflight,
        lease_state_reader=lambda: idle,
        main_sha_reader=lambda: main,
    )
    assert out["decision"] == "STOP"
    assert out["live_cursor_dispatch_authorized"] is False
    assert out["reason"] == "owner_activation_not_enabled"
    assert out.get("competing_writer") is not True

    blocked = run_gates_only(
        ctx,
        issue_preflight=lambda: good_preflight,
        lease_state_reader=lambda: busy,
        main_sha_reader=lambda: main,
    )
    assert blocked["reason"] == "global_lease_not_idle"
    assert blocked["competing_writer"] is True

    bad_ctx = ProtectedCursorContext(
        repository=CONTROL_REPO,
        actor=CONTROL_ACTOR,
        ref="refs/heads/main",
        event_name="workflow_dispatch",
        run_attempt="1",
        operation="wrong-operation",
        owner_go_issue=ISSUE,
        workflow_run_id="1",
        execute_cursor_requested=False,
    )
    assert validate_workflow_context(bad_ctx)["reason"] == "approved_operation_mismatch"

    assert validate_workflow_context(None)["reason"] == "protected_workflow_context_missing_or_untrusted"
    forbidden = run_gates_only(
        ctx,
        issue_preflight=lambda: good_preflight,
        lease_state_reader=lambda: idle,
        main_sha_reader=lambda: main,
        caller_context={"budget_controls_verified": True},
    )
    assert forbidden["reason"] == "caller_attestation_fields_not_trusted"

    msg = PREFIX + json.dumps(idle, separators=(",", ":"))
    assert parse_public_lease_state(msg)["phase"] == "IDLE"
    print("PASS: cursor protected dispatch gates-only fixtures; activation OFF")


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--gates-only", action="store_true",
                       help="Owner workflow audit; never POST Cursor")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    result = run_live_gates_only()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())