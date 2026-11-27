#!/usr/bin/env python3
"""Protected owner-triggered Cursor dispatch for Haversine Issue #220 only.

Routes one owner workflow_dispatch through the existing managed launch
transaction (managed_cursor_launch.launch_single_approved_issue). The permit is
derived here from workflow-observed evidence (live lease, live scope preflight,
GET-only Cursor inventory, /v1/models, /v1/me) plus labelled owner
attestations from repository variables; caller JSON flags are never trusted.
While PILOT_ACTIVATION_ENABLED is False no lease writer or Cursor POST client
is even constructed, so this module cannot acquire a lease or POST.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from cursor_pr_payload import PayloadError, single_issue_payload
from cursor_readonly import (
    CursorReadError, api_key_info_ok, from_environment, global_run_preflight, model_ids,
)
from github_ref_lease import (
    PREFIX, Controller, GitHubRefStore, agent_id_for, check_state, fingerprint,
)
import managed_cursor_launch  # flag read at call time in self_test
from managed_cursor_launch import (
    PILOT_ACTIVATION_ENABLED, CursorCreateHTTP, launch_single_approved_issue,
)
from openhands_issue_contract import PATH, REPO, live_preflight
from openhands_runner_admission_bridge import caller_json_carries_forbidden_attestation
from cursor_tasks import CursorTask, TASKS, task_for, task_for_issue_number
from sequential_handoff import request_id_for_issue

ISSUE = 220  # first pilot; every other task comes from cursor_tasks.TASKS
LEASE_REPO = "DaniilSydorenko/.github"
LEASE_REF = "ai-eng-cursor-lease-v1"
CONTROL_REPO = "DaniilSydorenko/.github"
CONTROL_ACTOR = "DaniilSydorenko"
APPROVED_OPERATION = "cursor-managed-delivery"
DEFAULT_MODEL = "composer-2"
MODEL_ALLOWLIST = frozenset({DEFAULT_MODEL})
TASK_220 = task_for(REPO, ISSUE)
assert TASK_220 is not None and TASK_220.allowed_paths == (PATH,)
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
        "issue": extra.pop("issue", ISSUE),
        "executor": "cursor",
        "live_cursor_dispatch_authorized": False,
        "cursor_post_attempted": False,
        "pilot_activation_enabled": PILOT_ACTIVATION_ENABLED is True,
        **extra,
    }


def owner_workflow_env_ok(environ: Mapping[str, str] | None = None,
                          operation: str = APPROVED_OPERATION) -> bool:
    """Owner workflow_dispatch of main, first attempt, in the control repository."""
    env = os.environ if environ is None else environ
    return (env.get("GITHUB_REPOSITORY") == CONTROL_REPO
            and env.get("GITHUB_ACTOR") == CONTROL_ACTOR
            and env.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
            and env.get("GITHUB_REF") == "refs/heads/main"
            and env.get("GITHUB_RUN_ATTEMPT") == "1"
            and bool(env.get("GITHUB_RUN_ID"))
            and env.get("AI_ENG_APPROVED_OPERATION") == operation)


def protected_context_from_env() -> ProtectedCursorContext | None:
    if not owner_workflow_env_ok():
        return None
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
    task = task_for_issue_number(int(issue_raw)) if (issue_raw or "").isdigit() else None
    if task is None:
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
        owner_go_issue=task.issue,
        workflow_run_id=run_id,
        execute_cursor_requested=execute,
    )


def task_for_context(ctx: ProtectedCursorContext | None) -> CursorTask | None:
    return None if ctx is None else task_for_issue_number(ctx.owner_go_issue)


def validate_workflow_context(ctx: ProtectedCursorContext | None) -> dict[str, Any] | None:
    if ctx is None:
        return _stop("protected_workflow_context_missing_or_untrusted")
    if task_for_context(ctx) is None:
        return _stop("owner_go_issue_not_registered", issue=ctx.owner_go_issue)
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


def request_id_for_dispatch(task: CursorTask | None = None) -> str:
    """Deterministic per-Issue id shared with sequential_handoff (replay key).

    A per-workflow-run id would mint a fresh request on every dispatch and make
    the lease replay ledger useless; it would also never match the handoff's
    proposed_request_id that launch_single_approved_issue requires.
    """
    task = task or TASK_220
    return request_id_for_issue(task.repository, task.issue)


def build_proposal(*, request_id: str, main_sha: str,
                   task: CursorTask | None = None) -> dict[str, Any]:
    task = task or TASK_220
    try:
        return single_issue_payload(
            request_id=request_id,
            repository=task.repository,
            issue_number=task.issue,
            exact_default_sha=main_sha,
            allowed_paths=list(task.allowed_paths),
            model_id=task.model,
            model_allowlist=frozenset({task.model}),
        )
    except PayloadError as exc:
        return _stop("cursor_payload_invalid", detail=str(exc))


# Facts no API can prove. The owner sets these as repository variables; the
# workflow injects them. They are labelled attestations, never "verified" proof.
OWNER_ATTESTATIONS = {
    "verified_cursor_billing": "AI_ENG_ATTEST_CURSOR_SPEND_LIMIT_SET",
    "verified_external_billing_excluded": "AI_ENG_ATTEST_NO_EXTERNAL_BILLING",
    "verified_subagents_disabled": "AI_ENG_ATTEST_SUBAGENTS_DISABLED",
    "verified_launch_route_exclusivity": "AI_ENG_ATTEST_SINGLE_LAUNCH_ROUTE",
    "verified_owner_security_gates": "AI_ENG_ATTEST_TARGET_BRANCH_PROTECTED",
    "account_scope_attested": "AI_ENG_ATTEST_CURSOR_KEY_ACCOUNT_SCOPE",
}
ATTESTED = "true"


def attestations_from_env(environ: Mapping[str, str] | None = None) -> dict[str, bool]:
    env = os.environ if environ is None else environ
    return {key: env.get(var) == ATTESTED for key, var in OWNER_ATTESTATIONS.items()}


def build_trusted_permit(
    ctx: ProtectedCursorContext,
    *,
    request_id: str,
    main_sha: str,
    scope_preflight_passed: bool,
    attestations: Mapping[str, bool],
    key_info_ok: bool,
    live_models: frozenset[str],
    inventory: Mapping[str, Any] | None,
    task: CursorTask | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Derive the managed-launch permit from workflow-observed evidence only.

    Returns (permit, missing_evidence). Caller JSON never reaches this function.
    """
    task = task or TASK_220
    account_scope = (attestations.get("account_scope_attested") is True
                     and key_info_ok is True)
    flags = {
        # ctx exists only for an owner workflow_dispatch on main, attempt 1, in
        # the protected ai-eng-lease-owner environment (validated earlier).
        "verified_owner_approval": validate_workflow_context(ctx) is None,
        "verified_exact_scope": scope_preflight_passed is True,
        "verified_account_scope": account_scope,
        "verified_model_allowlist": task.model in live_models,
        **{key: attestations.get(key) is True for key in (
            "verified_cursor_billing", "verified_external_billing_excluded",
            "verified_subagents_disabled", "verified_launch_route_exclusivity",
            "verified_owner_security_gates")},
    }
    missing = sorted(k for k, v in flags.items() if v is not True)
    if not isinstance(inventory, Mapping) or inventory.get("status") != "CLEAR":
        missing.append("cursor_inventory_clear")
    permit = {
        **flags,
        "request_id": request_id,
        "proposed_request_id": request_id,
        "repository": task.repository,
        "issue_number": task.issue,
        "head_sha": main_sha,
        "model_id": task.model,
        "model_allowlist": frozenset({task.model}),
    }
    return permit, missing


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
    if state == "STARTED":
        return {
            "decision": "STARTED",
            "reason": launch.get("reason"),
            "issue": launch.get("issue", ISSUE),
            "executor": "cursor",
            "live_cursor_dispatch_authorized": True,
            "cursor_post_attempted": True,
            "pilot_activation_enabled": True,
            "managed_launch_state": state,
            "agent_id": launch.get("agent_id"),
            "run_id": launch.get("run_id"),
        }
    return _stop(
        "managed_launch_" + str(launch.get("reason") or "stopped"),
        managed_launch_state=state,
        managed_launch_reason=launch.get("reason"),
        # STOP_LOCK_HELD means a POST may have happened: never report "no POST".
        cursor_post_attempted=state == "STOP_LOCK_HELD",
    )


def run_gates_only(
    ctx: ProtectedCursorContext,
    *,
    issue_preflight: Callable[[], dict[str, Any]],
    lease_state_reader: Callable[[], dict[str, Any]],
    main_sha_reader: Callable[[], str],
    caller_context: Mapping[str, Any] | None = None,
    cursor_api: Any = None,
    attestations: Mapping[str, bool] | None = None,
    launch_bundle: dict[str, Any] | None = None,
    bundle_builder: Callable[..., dict[str, Any]] | None = None,
    controller: Any = None,
    cursor_create: Any = None,
) -> dict[str, Any]:
    """Owner-triggered path through the real managed launch. Fail-closed.

    bundle_builder(task=, main_sha=, lease_state=, inventory=) returns the
    {"preview", "handoff"} bundle from live evidence, or a STOP dict.
    """
    blocked = validate_workflow_context(ctx)
    if blocked is not None:
        return blocked
    task = task_for_context(ctx)
    assert task is not None  # validate_workflow_context guarantees it
    forbidden = caller_json_carries_forbidden_attestation(caller_context or {})
    if forbidden:
        return _stop("caller_attestation_fields_not_trusted", forbidden_keys=sorted(forbidden))
    rid = request_id_for_dispatch(task)
    try:
        lease_state = lease_state_reader()
    except (ValueError, TypeError, KeyError, OSError) as exc:
        # OSError covers urllib HTTPError/URLError and timeouts: fail closed.
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
    if fingerprint(rid) in lease_state.get("consumed_request_hashes", []):
        return _stop("request_already_consumed", request_id=rid)
    try:
        preflight = issue_preflight()
    except (ValueError, TypeError, KeyError, OSError) as exc:
        return _stop("issue_preflight_unavailable", error_type=type(exc).__name__)
    if not isinstance(preflight, dict):
        return _stop("issue_preflight_invalid")
    if preflight.get("reason") != "scope_preflight_passed_but_live_gates_unverified":
        return _stop(
            "issue_preflight_" + str(preflight.get("reason", "failed")),
            preflight_decision=preflight.get("decision"),
        )
    try:
        main_sha = main_sha_reader()
    except (ValueError, TypeError, KeyError, OSError) as exc:
        return _stop("default_branch_sha_unavailable", error_type=type(exc).__name__)
    if not isinstance(main_sha, str) or not SHA.fullmatch(main_sha):
        return _stop("invalid_default_branch_sha")
    proposal = build_proposal(request_id=rid, main_sha=main_sha, task=task)
    if proposal.get("decision") == "STOP":
        return proposal

    # Provider evidence: GET-only. No key => evidence missing, never assumed.
    attested = dict(attestations or {})
    inventory: dict[str, Any] | None = None
    models: frozenset[str] = frozenset()
    key_ok = False
    if cursor_api is not None:
        key_ok = api_key_info_ok(cursor_api)
        models = model_ids(cursor_api)
        inventory = global_run_preflight(
            cursor_api,
            global_account_scope_verified=attested.get("account_scope_attested") is True
            and key_ok,
        )
        if inventory.get("status") == "BUSY":
            return _stop("cursor_agent_busy", cursor_inventory=inventory)
    permit, missing = build_trusted_permit(
        ctx, request_id=rid, main_sha=main_sha,
        scope_preflight_passed=True, attestations=attested,
        key_info_ok=key_ok, live_models=models, inventory=inventory, task=task,
    )
    bundle = launch_bundle if launch_bundle is not None else {}
    if not missing and bundle_builder is not None and launch_bundle is None:
        try:
            bundle = bundle_builder(task=task, main_sha=main_sha,
                                    lease_state=lease_state, inventory=inventory)
        except (ValueError, TypeError, KeyError, OSError) as exc:
            return _stop("launch_bundle_unavailable", error_type=type(exc).__name__,
                         request_id=rid, issue=task.issue)
        if bundle.get("decision") == "STOP":
            return _stop("launch_bundle_" + str(bundle.get("reason")), request_id=rid,
                         issue=task.issue, bundle_detail=bundle.get("detail"))
    launch = launch_single_approved_issue(
        request_id=rid,
        bundle=bundle,
        permit=permit if not missing else {},
        controller=controller,
        cursor_reader=cursor_api,
        cursor_create=cursor_create,
    )
    result = summarize_launch_attempt(launch, proposal=proposal)
    result.update(
        {
            "request_id": rid,
            "issue": task.issue,
            "preflight_reason": preflight.get("reason"),
            "permit_missing_evidence": missing,
            "cursor_inventory": inventory,
            "proposal_agent_id": agent_id_for(rid),
            "exact_head_verification": "pending_after_terminal_run",
            # Sanitized GET evidence so a missing permit item names its cause
            # (rejected key vs. pinned model not offered). Public model ids only.
            "cursor_provider_evidence": {
                "api_configured": cursor_api is not None,
                "key_info_ok": key_ok,
                "pinned_model": task.model,
                "live_model_ids": sorted(models)[:50],
            },
        }
    )
    return result


def _github_get(repo: str, path: str) -> dict[str, Any]:
    """Unauthenticated public GET; the repository is always explicit."""
    if repo != LEASE_REPO and not any(t.repository == repo for t in TASKS):
        raise ValueError("github_repository_not_allowlisted")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}{path}",
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
    ref = _github_get(LEASE_REPO, f"/git/ref/heads/{LEASE_REF}")
    sha = ((ref.get("object") or {}).get("sha"))
    if not isinstance(sha, str):
        raise ValueError("lease_ref_missing")
    commit = _github_get(LEASE_REPO, "/git/commits/" + sha)
    return parse_public_lease_state(commit.get("message") or "")


def live_main_sha(task: CursorTask | None = None) -> str:
    task = task or TASK_220
    repo = _github_get(task.repository, "")
    branch = repo.get("default_branch")
    if branch != task.default_branch:
        raise ValueError("unexpected_default_branch")
    ref = _github_get(task.repository, f"/git/ref/heads/{branch}")
    sha = ((ref.get("object") or {}).get("sha"))
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise ValueError("invalid_master_sha")
    return sha


def _live_writers() -> tuple[Any, Any]:
    """Lease writer and Cursor POST client exist only once activation is ON."""
    if PILOT_ACTIVATION_ENABLED is not True:
        return None, None
    token = os.environ.get("AI_ENG_LEASE_WRITER_TOKEN")
    key = os.environ.get("CURSOR_API_KEY")
    if not token or not key:
        return None, None
    return (Controller(GitHubRefStore(LEASE_REPO, token, LEASE_REF)),
            CursorCreateHTTP(key))


def run_live_gates_only() -> dict[str, Any]:
    ctx = protected_context_from_env()
    try:
        cursor_api = from_environment() if os.environ.get("CURSOR_API_KEY") else None
    except CursorReadError:
        cursor_api = None
    controller, cursor_create = _live_writers()
    return run_gates_only(
        ctx,  # type: ignore[arg-type]
        issue_preflight=live_preflight,
        lease_state_reader=live_lease_state,
        main_sha_reader=live_main_sha,
        cursor_api=cursor_api,
        attestations=attestations_from_env(),
        controller=controller,
        cursor_create=cursor_create,
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
    assert out.get("cursor_post_attempted") is not True
    # The workflow runs this before every live step, so it must hold with the
    # flag in either state: OFF stops first; ON must still fail closed here
    # because no provider evidence or owner attestation is supplied.
    assert out["reason"] == (
        "managed_launch_trusted_owner_finance_or_scope_proof_missing"
        if managed_cursor_launch.PILOT_ACTIVATION_ENABLED is True
        else "owner_activation_not_enabled"
    )
    assert out["permit_missing_evidence"], "self-test fixture must never be admissible"
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
    print("PASS: cursor protected dispatch gates-only fixtures; activation "
          + ("ON (fail-closed)" if managed_cursor_launch.PILOT_ACTIVATION_ENABLED is True
             else "OFF"))


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