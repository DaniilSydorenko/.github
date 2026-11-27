#!/usr/bin/env python3
"""One bounded step of the managed Cursor delivery cycle, chosen by lease phase.

    IDLE        -> trusted bundle + permit -> managed launch (activation gated)
    DISPATCHING -> read deterministic agent id: RUNNING, or BLOCKED if absent
    RUNNING     -> bounded GET-only observation; terminal -> VERIFYING
    VERIFYING   -> discover + verify PR, bind it; then exact-head acceptance;
                   owner-merged verified head -> release_verified (lease IDLE)
    BLOCKED     -> owner decision only (reject action)

Each protected workflow run performs ONE step and exits. Nothing here POSTs to
Cursor except managed_cursor_launch (gated by PILOT_ACTIVATION_ENABLED), and
nothing merges: an eligible PR is handed to the owner. Uncertain provider state
always keeps the lease; no step ever launches a replacement agent.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable, Mapping

from cursor_acceptance import ELIGIBLE, evaluate
from cursor_bundle_builder import build_launch_bundle, open_pull_requests
from cursor_execution_observer import (
    github_actions_run_id, observe_once, observe_run, provider_quiescent, reconcile_dispatching,
)
from cursor_pr_binding import PR_URL, discover_and_verify
from cursor_protected_dispatch import (
    APPROVED_OPERATION, LEASE_REF, LEASE_REPO, OWNER_ATTESTATIONS, ProtectedCursorContext,
    attestations_from_env, live_lease_state, owner_workflow_env_ok,
    protected_context_from_env, run_gates_only, task_for_context,
)
from cursor_readonly import global_run_preflight
from cursor_tasks import TASKS, CursorTask, task_for, task_for_issue_number
from github_ref_lease import Controller, GitHubRefStore, LeaseError, fingerprint

REJECT_OPERATION = "cursor-lease-reject"
# Owner-free diagnostics job (ai-eng-cursor-api-probe.yml). Distinct operation:
# protected_context_from_env() rejects it, so it can never drive a privileged step.
READONLY_OPERATION = "cursor-readonly-preflight"
# Permit items only the privileged environment's owner attestations can satisfy.
# The read-only job cannot see those variables, so it reports them separately.
ATTESTATION_GATED = frozenset(OWNER_ATTESTATIONS) | {"verified_account_scope",
                                                     "cursor_inventory_clear"}
# One owner-approved privileged run may chain lifecycle steps up to this bound.
MAX_STEPS_PER_RUN = 10


def _out(step: str, outcome: str, **fields: Any) -> dict[str, Any]:
    return {"step": step, "outcome": outcome, "automatic_merge": False, **fields}


def _task_from_lease(state: Mapping[str, Any]) -> CursorTask | None:
    source = state.get("source_issue_url") or ""
    parts = source.split("/")
    if len(parts) == 7 and parts[5] == "issues" and parts[6].isdigit():
        return task_for(f"{parts[3]}/{parts[4]}", int(parts[6]))
    return None


def _starting_sha(cursor_api: Any, agent_id: str, task: CursorTask) -> str | None:
    """The startingRef we sent, read back from the deterministic agent."""
    try:
        agent = cursor_api.get_json(f"/v1/agents/{agent_id}")
    except Exception:  # noqa: BLE001 - any provider failure => unknown
        return None
    repos = agent.get("repos") if isinstance(agent, dict) else None
    want = "https://github.com/" + task.repository
    refs = [r.get("startingRef") for r in repos or [] if isinstance(r, dict) and r.get("url") == want]
    ref = refs[0] if len(refs) == 1 else None
    return ref if isinstance(ref, str) and len(ref) == 40 else None


def step_verifying(*, controller: Controller, state: Mapping[str, Any], task: CursorTask,
                   gh: Any, cursor_api: Any) -> dict[str, Any]:
    rid, agent_id = state["request_id"], state.get("agent_id")
    source, pr_url = state.get("source_issue_url"), state.get("pr_url")
    if cursor_api is None:
        return _out("verify", "HOLD", reason="cursor_api_unavailable")
    starting = _starting_sha(cursor_api, agent_id, task)
    if starting is None:
        return _out("verify", "HOLD", reason="starting_sha_unverifiable")
    if pr_url == source:
        obs = observe_once(cursor_api, agent_id, state.get("run_id"), now=0)
        branches = obs.get("branches", [])
    else:
        branches = [{"repoUrl": "github.com/" + task.repository, "prUrl": pr_url}]
    found = discover_and_verify(gh, task, provider_branches=branches, starting_sha=starting,
                                allow_merged=pr_url != source)
    if found["decision"] == "NO_PR":
        return _out("verify", "OWNER_ACTION", reason="no_pr_produced",
                    owner_action="reject with pr_url = " + str(source))
    if found["decision"] == "REJECTED":
        return _out("verify", "OWNER_ACTION", reason=found["reason"],
                    owner_action="reject with pr_url = " + str(pr_url))
    if found["decision"] != "BIND":
        return _out("verify", "HOLD", reason=found["reason"], detail=found)
    if pr_url == source:
        controller.bind_generated_pr(rid, expected_issue_url=source,
                                     generated_pr_url=found["pr_url"])
    verdict = evaluate(gh, task, pr_number=found["pr_number"], bound_head_sha=found["head_sha"])
    if verdict["status"] == "INTEGRATED":
        controller.release_verified(rid, provider_terminal=True, integration_accepted=True,
                                    manual_approval=True)
        return _out("verify", "RELEASED", pr=found["pr_url"], acceptance=verdict,
                    next_task="select via sequential_handoff (previous_pr input)")
    if verdict["status"] == ELIGIBLE:
        return _out("verify", "INTEGRATION_READY", pr=found["pr_url"], acceptance=verdict,
                    owner_action="review and merge the exact head; then run advance")
    if verdict["status"] == "REJECTED":
        return _out("verify", "OWNER_ACTION", pr=found["pr_url"], acceptance=verdict,
                    owner_action="close the PR, then run reject")
    return _out("verify", "HOLD", pr=found["pr_url"], acceptance=verdict)


def advance(*, store: Any, gh: Any, cursor_api: Any, ctx: Any,
            attestations: Mapping[str, bool], dispatch: Callable[..., dict[str, Any]],
            max_polls: int = 10, interval_s: float = 30.0,
            sleep: Callable[[float], None] | None = None) -> dict[str, Any]:
    controller = Controller(store)
    snap = store.read()
    state, phase = snap.state, snap.state.get("phase")
    if phase == "IDLE":
        return _out("dispatch", "DISPATCH_ATTEMPTED", result=dispatch(snap.state))
    task = _task_from_lease(state)
    if task is None:
        return _out("observe", "OWNER_ACTION", reason="lease_not_owned_by_registered_cursor_task",
                    lease_phase=phase, owner_action="reconcile with reject")
    rid, agent_id = state["request_id"], state.get("agent_id")
    if phase == "DISPATCHING":
        if cursor_api is None:
            return _out("reconcile", "HOLD", reason="cursor_api_unavailable")
        found = reconcile_dispatching(cursor_api, agent_id)
        if found["state"] == "RUN_FOUND":
            controller.transition(rid, "DISPATCHING", "RUNNING", run_id=found["run_id"])
            return _out("reconcile", "RUNNING", run_id=found["run_id"])
        if found["state"] == "AGENT_ABSENT":
            controller.transition(rid, "DISPATCHING", "BLOCKED")
            return _out("reconcile", "BLOCKED", reason=found["reason"],
                        owner_action="reject with pr_url = " + str(state.get("source_issue_url")))
        return _out("reconcile", "HOLD", reason=found["reason"])
    if phase == "RUNNING":
        if cursor_api is None:
            return _out("observe", "HOLD", reason="cursor_api_unavailable")
        kwargs = {"max_polls": max_polls, "interval_s": interval_s}
        if sleep is not None:
            kwargs["sleep"] = sleep
        obs = observe_run(cursor_api, agent_id, state.get("run_id"), **kwargs)
        if obs["state"] in ("SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED"):
            controller.transition(rid, "RUNNING", "VERIFYING")
            return _out("observe", "VERIFYING", observation=obs)
        return _out("observe", "HOLD", observation=obs)
    if phase == "VERIFYING":
        return step_verifying(controller=controller, state=state, task=task, gh=gh,
                              cursor_api=cursor_api)
    return _out("observe", "OWNER_ACTION", reason="lease_blocked", lease_phase=phase,
                owner_action="reject after verifying the provider is quiescent")


def reject(*, store: Any, gh: Any, cursor_api: Any, request_id: str,
           expected_lease_sha: str, pr_url: str, owner_authorized: bool) -> dict[str, Any]:
    """Owner-authorized, evidence-checked, CAS-bound, idempotent rejected release."""
    if owner_authorized is not True:
        return _out("reject", "STOP", reason="owner_authorization_missing")
    snap = store.read()
    state = snap.state
    if state.get("phase") == "IDLE":
        if fingerprint(request_id) in state.get("consumed_request_hashes", []):
            return _out("reject", "ALREADY_RELEASED", lease_sha=snap.sha)
        return _out("reject", "STOP", reason="lease_idle_request_unknown")
    if snap.sha != expected_lease_sha:
        return _out("reject", "STOP", reason="stale_lease_revision",
                    observed_lease_sha=snap.sha, revision=state.get("revision"))
    if state.get("request_id") != request_id or state.get("pr_url") != pr_url:
        return _out("reject", "STOP", reason="lease_identity_mismatch")
    if state.get("phase") not in ("VERIFYING", "BLOCKED"):
        return _out("reject", "STOP", reason="lease_phase_not_terminal", lease_phase=state.get("phase"))
    source = state.get("source_issue_url") or ""
    repo = "/".join(source.split("/")[3:5])
    if not any(t.repository == repo for t in TASKS):
        return _out("reject", "STOP", reason="lease_repository_not_allowlisted")

    # Rejection evidence (runtime): PR closed unmerged, or no Cursor PR exists.
    match = PR_URL.fullmatch(pr_url)
    if match:
        if match.group(1) != repo:
            return _out("reject", "STOP", reason="pr_not_in_lease_repository")
        pr = gh.get_json(f"/repos/{repo}/pulls/{match.group(2)}")
        rejection = (isinstance(pr, dict) and pr.get("state") == "closed"
                     and pr.get("merged") is not True)
        if not rejection:
            return _out("reject", "STOP", reason="pr_not_closed_unmerged")
    elif pr_url == source:
        open_prs = open_pull_requests(gh, repo)
        if open_prs is None or any(str((p.get("head") or {}).get("ref", "")).startswith("cursor/")
                                   for p in open_prs):
            return _out("reject", "STOP", reason="open_cursor_pr_may_exist")
    else:
        return _out("reject", "STOP", reason="unsupported_lease_target")

    # Provider evidence (runtime): no managed execution may still be active.
    run_id, agent_id = state.get("run_id"), state.get("agent_id")
    actions_run = github_actions_run_id(run_id)
    if actions_run is not None:
        run = gh.get_json(f"/repos/{LEASE_REPO}/actions/runs/{actions_run}")
        if not (isinstance(run, dict) and run.get("status") == "completed"):
            return _out("reject", "STOP", reason="legacy_executor_run_not_completed")
    else:
        if cursor_api is None:
            return _out("reject", "STOP", reason="cursor_api_unavailable")
        quiet = provider_quiescent(cursor_api, agent_id)
        if quiet["quiescent"] is not True:
            return _out("reject", "STOP", reason="provider_not_quiescent", detail=quiet)
    try:
        released = Controller(store).release_rejected(
            request_id, expected_sha=expected_lease_sha, pr_url=pr_url,
            provider_terminal=True, rejection_verified=True, manual_approval=True)
    except LeaseError as exc:  # includes RefConflict: never retried
        return _out("reject", "STOP", reason="lease_write_refused", error=str(exc))
    return _out("reject", released, request_id=request_id)


def _live() -> tuple[Any, Any, Any] | None:
    from cursor_readonly import CursorReadError, from_environment
    from trusted_github_evidence import LiveGitHub

    token = os.environ.get("AI_ENG_LEASE_WRITER_TOKEN")
    gh_token = os.environ.get("GH_TOKEN")
    if not token or not gh_token:
        return None
    try:
        cursor_api = from_environment() if os.environ.get("CURSOR_API_KEY") else None
    except CursorReadError:
        cursor_api = None
    return GitHubRefStore(LEASE_REPO, token, LEASE_REF), LiveGitHub(gh_token), cursor_api


def _readonly_main() -> dict[str, Any]:
    """No lease-writer token is read; a present one is refused (wrong job)."""
    from cursor_readonly import CursorReadError, from_environment
    from trusted_github_evidence import LiveGitHub

    if os.environ.get("AI_ENG_LEASE_WRITER_TOKEN"):
        return _out("preflight", "STOP", reason="writer_credential_in_readonly_job")
    if readonly_context_from_env() is None:
        return _out("preflight", "STOP", reason="readonly_workflow_context_missing_or_untrusted")
    gh_token = os.environ.get("GH_TOKEN")
    if not gh_token:
        return _out("preflight", "STOP", reason="github_token_missing")
    try:
        cursor_api = from_environment() if os.environ.get("CURSOR_API_KEY") else None
    except CursorReadError:
        cursor_api = None
    gh = LiveGitHub(gh_token)
    return readonly_preflight(
        lease_state_reader=live_lease_state, cursor_api=cursor_api,
        dispatch=_live_dispatch(gh, cursor_api, bootstrap=True, previous_pr=None, readonly=True))


def _live_dispatch(gh: Any, cursor_api: Any, *, bootstrap: bool,
                   previous_pr: int | None,
                   readonly: bool = False) -> Callable[[Mapping[str, Any]], dict[str, Any]]:
    from cursor_protected_dispatch import _live_writers, live_main_sha
    from openhands_issue_contract import live_preflight
    from trusted_github_evidence import collect_task_evidence

    def dispatch(lease_state: Mapping[str, Any]) -> dict[str, Any]:
        ctx = readonly_context_from_env() if readonly else protected_context_from_env()
        task = task_for_context(ctx)
        if task is None:
            return {"decision": "STOP", "reason": "protected_workflow_context_missing_or_untrusted"}
        collected = collect_task_evidence(task.repository, task.issue, transport=gh)

        def preflight() -> dict[str, Any]:
            if task.issue == 220:
                return live_preflight()
            facts = collected.get("observed_facts") or {}
            ok = collected.get("status") == "OBSERVED" and facts.get("issue_state") == "open"
            return {"decision": "STOP", "reason": "scope_preflight_passed_but_live_gates_unverified"
                    if ok else "issue_not_open_or_unobserved"}

        def builder(*, task, main_sha, lease_state, inventory):
            del inventory  # provider evidence already enforced by the permit
            return build_launch_bundle(gh, task, collected=collected, main_sha=main_sha,
                                       lease_state=lease_state,
                                       owner_bootstrap_authorized=bootstrap,
                                       previous_pr_number=previous_pr)

        # Read-only: no writer, no POST client, no attestations, whatever the
        # activation flag or environment says. The permit can never be complete.
        controller, cursor_create = (None, None) if readonly else _live_writers()
        return run_gates_only(
            ctx, issue_preflight=preflight, lease_state_reader=lambda: dict(lease_state),
            main_sha_reader=lambda: live_main_sha(task), cursor_api=cursor_api,
            attestations={} if readonly else attestations_from_env(), bundle_builder=builder,
            controller=controller, cursor_create=cursor_create)

    return dispatch


def readonly_context_from_env() -> ProtectedCursorContext | None:
    """Owner/main/attempt-1 context for the owner-free diagnostics job.

    Requires AI_ENG_APPROVED_OPERATION == READONLY_OPERATION, so the privileged
    context reader rejects the same environment. The gate evaluation sees the
    privileged operation only to report what that run would check; readonly
    dispatch passes no writer and no attestations, so nothing can launch.
    """
    if not owner_workflow_env_ok(operation=READONLY_OPERATION):
        return None
    raw = os.environ.get("AI_ENG_OWNER_GO_ISSUE", "")
    task = task_for_issue_number(int(raw)) if raw.isdigit() else None
    if task is None:
        return None
    return ProtectedCursorContext(
        repository=os.environ["GITHUB_REPOSITORY"], actor=os.environ["GITHUB_ACTOR"],
        ref=os.environ["GITHUB_REF"], event_name=os.environ["GITHUB_EVENT_NAME"],
        run_attempt=os.environ["GITHUB_RUN_ATTEMPT"], operation=APPROVED_OPERATION,
        owner_go_issue=task.issue, workflow_run_id=os.environ["GITHUB_RUN_ID"],
        execute_cursor_requested=False)


def readonly_preflight(*, lease_state_reader: Callable[[], Mapping[str, Any]],
                       cursor_api: Any,
                       dispatch: Callable[[Mapping[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    """Owner-free diagnostics: public lease read, gates, GET-only provider evidence.

    Never acquires or writes the lease and never POSTs (see readonly dispatch).
    Attestation-gated permit items are reported apart from the rest, because
    only the privileged environment holds the owner attestations.
    """
    try:
        state = lease_state_reader()
    except (ValueError, TypeError, KeyError, OSError) as exc:
        return _out("preflight", "STOP", reason="lease_state_unreadable",
                    error_type=type(exc).__name__, read_only=True)
    phase = state.get("phase")
    gates = None
    if phase == "IDLE":
        r = dispatch(state)
        missing = list(r.get("permit_missing_evidence") or [])
        gates = {
            "decision": r.get("decision"), "reason": r.get("reason"),
            "cursor_post_attempted": r.get("cursor_post_attempted"),
            "request_id": r.get("request_id"),
            "missing_excluding_attestations": sorted(m for m in missing
                                                     if m not in ATTESTATION_GATED),
            "attestation_gated_items": sorted(m for m in missing if m in ATTESTATION_GATED),
            "cursor_provider_evidence": r.get("cursor_provider_evidence"),
        }
    # Observation only: never feeds a permit (the privileged run re-reads it
    # under the account-scope attestation before any launch).
    inventory = (global_run_preflight(cursor_api, global_account_scope_verified=True)
                 if cursor_api is not None else None)
    return _out("preflight", "READ_ONLY", read_only=True, lease_phase=phase,
                lease_revision=state.get("revision"), lease_request_id=state.get("request_id"),
                gates=gates, cursor_inventory_observed=inventory,
                attestations="evaluated_only_in_privileged_run")


def _progressing(result: Mapping[str, Any]) -> bool:
    """True only when the next lifecycle step needs no owner decision."""
    step, outcome = result.get("step"), result.get("outcome")
    if step == "dispatch":
        return (result.get("result") or {}).get("decision") == "STARTED"
    if step == "reconcile":
        return outcome == "RUNNING"
    if step == "observe":
        return outcome == "VERIFYING" or (
            outcome == "HOLD" and (result.get("observation") or {}).get("state") == "IN_PROGRESS")
    return False


def advance_until_owner_action(
        *, max_steps: int,
        advance_once: Callable[[Callable[[Mapping[str, Any]], dict[str, Any]]], dict[str, Any]],
        dispatch: Callable[[Mapping[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    """Chain lifecycle steps inside ONE owner-approved privileged run.

    Bounded standing authorization: the deployment approval covers dispatch ->
    observe -> verify for the registered task, and stops at the first step that
    needs the owner (merge, reject, ambiguity) or at max_steps. At most one
    dispatch per run: a later IDLE lease (e.g. after release) never launches.
    """
    if type(max_steps) is not int or not 1 <= max_steps <= MAX_STEPS_PER_RUN:
        return _out("advance", "STOP", reason="invalid_step_budget")
    dispatched: list[bool] = []

    def dispatch_once(state: Mapping[str, Any]) -> dict[str, Any]:
        if dispatched:
            return {"decision": "STOP", "reason": "one_dispatch_per_run",
                    "cursor_post_attempted": False}
        dispatched.append(True)
        return dispatch(state)

    trail: list[dict[str, Any]] = []
    result: dict[str, Any] = {}
    for _ in range(max_steps):
        result = advance_once(dispatch_once)
        trail.append({"step": result.get("step"), "outcome": result.get("outcome"),
                      "reason": result.get("reason")
                      or (result.get("result") or {}).get("reason")})
        if not _progressing(result):
            break
    return {**result, "lifecycle_steps": trail}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    adv = sub.add_parser("advance")
    adv.add_argument("--bootstrap", action="store_true")
    adv.add_argument("--previous-pr", type=int)
    adv.add_argument("--max-polls", type=int, default=10)
    adv.add_argument("--max-steps", type=int, default=1)
    rej = sub.add_parser("reject")
    rej.add_argument("--request-id", required=True)
    rej.add_argument("--expected-lease-sha", required=True)
    rej.add_argument("--pr-url", required=True)
    sub.add_parser("preflight")
    args = parser.parse_args(argv)
    if args.action == "preflight":
        result = _readonly_main()
        print(json.dumps(result, sort_keys=True, default=str))
        return 0 if result.get("outcome") == "READ_ONLY" else 3
    live = _live()
    if live is None:
        print(json.dumps(_out("setup", "STOP", reason="github_tokens_missing"), sort_keys=True))
        return 3
    store, gh, cursor_api = live
    if args.action == "advance":
        if protected_context_from_env() is None:
            result = _out("advance", "STOP", reason="protected_workflow_context_missing_or_untrusted")
        else:
            ctx = protected_context_from_env()
            result = advance_until_owner_action(
                max_steps=args.max_steps,
                advance_once=lambda once: advance(
                    store=store, gh=gh, cursor_api=cursor_api, ctx=ctx,
                    attestations=attestations_from_env(), dispatch=once,
                    max_polls=args.max_polls),
                dispatch=_live_dispatch(gh, cursor_api, bootstrap=args.bootstrap,
                                        previous_pr=args.previous_pr))
    else:
        result = reject(store=store, gh=gh, cursor_api=cursor_api, request_id=args.request_id,
                        expected_lease_sha=args.expected_lease_sha, pr_url=args.pr_url,
                        owner_authorized=owner_workflow_env_ok(operation=REJECT_OPERATION))
    print(json.dumps(result, sort_keys=True, default=str))
    return 0 if result.get("outcome") not in ("STOP",) else 3


if __name__ == "__main__":
    sys.exit(main())
