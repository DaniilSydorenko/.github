"""Stage 2: single-owner, single-PR managed Cursor launch transaction.

OFF BY DEFAULT: this module does not activate GitHub workflows or Scheduled Tasks.
PILOT_ACTIVATION_ENABLED must be changed by a separately reviewed owner gate.
Caller-provided permit flags are NOT trusted authentication; the future runner
must derive them independently from protected GitHub/provider controls.
"""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cursor_pr_payload import existing_pr_payload, single_issue_payload
from cursor_readonly import global_run_preflight
from github_ref_lease import Controller, GitHubRefStore, LeaseError, agent_id_for
from lease_ref_protection import REPO as LEASE_REPO, REF as LEASE_REF, public_readonly_probe
from preview_one import preview_one
from sequential_handoff import preview_next_after_merge

PILOT_ACTIVATION_ENABLED = False


def _trusted_lease_ref_audit(controller: Controller) -> bool:
    """Never accept permit flags as proof of immutable, exclusive ref custody.

    Only the actual authenticated GH ref store may supply evidence. Owner
    must provision an explicitly approved single GitHub App as writer; unknown
    effective protections or API permissions => False. This is one necessary
    condition, NOT total proof of account exclusivity or financial safety.
    """
    store = controller.store
    if (not isinstance(store, GitHubRefStore)
            or store.api != "https://api.github.com/repos/" + LEASE_REPO
            or store.ref != LEASE_REF):
        return False
    expected_writer_app = os.getenv("AI_ENG_APPROVED_WRITER_APP")
    try:
        result = public_readonly_probe(
            lambda path: store._call("GET", path),
            approved_writer_app=expected_writer_app,
        )
    except (LeaseError, ValueError, TypeError):
        return False
    return result.get("status") == "VERIFIED"


class LaunchUncertain(RuntimeError):
    """Could have started; preserve DISPATCHING lease. Never retry blindly."""


class CursorCreateHTTP:
    """Only POST /v1/agents; never edit permissions or billing."""

    def __init__(self, api_key: str):
        if not isinstance(api_key, str) or not api_key:
            raise ValueError("Missing API credential")
        self._key = api_key

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        if (not isinstance(payload, dict) or set(payload) != {
            "agentId", "prompt", "model", "repos", "workOnCurrentBranch",
            "autoCreatePR", "mode",
        } or payload.get("mode") != "agent"
                or not isinstance(payload.get("repos"), list)
                or len(payload["repos"]) != 1
                or not isinstance(payload["repos"][0], dict)
                or not isinstance(payload.get("prompt"), dict)
                or set(payload["prompt"]) != {"text"}
                or not isinstance(payload["prompt"]["text"], str)
                or not payload["prompt"]["text"]):
            raise LaunchUncertain("Invalid restricted Cursor create payload")
        entry = payload["repos"][0]
        prior_pr = (set(entry) == {"url", "prUrl"}
                    and payload.get("workOnCurrentBranch") is True
                    and payload.get("autoCreatePR") is False)
        new_issue = (set(entry) == {"url", "startingRef"}
                     and payload.get("workOnCurrentBranch") is False
                     and payload.get("autoCreatePR") is True
                     and isinstance(entry.get("startingRef"), str)
                     and len(entry["startingRef"]) == 40
                     and all(c in "0123456789abcdef" for c in entry["startingRef"]))
        if not (prior_pr or new_issue):
            raise LaunchUncertain("Invalid restricted Cursor create mode")
        req = Request(
            "https://api.cursor.com/v1/agents",
            method="POST",
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + self._key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(req, timeout=20) as resp:
                obj = json.load(resp)
        except HTTPError as exc:
            # 409 may mean first idempotent create succeeded but reply was lost.
            # No response body or token goes into logs.
            raise LaunchUncertain(f"Cursor HTTP {exc.code}; no automatic retry") from None
        except (URLError, TimeoutError, OSError, ValueError, UnicodeError):
            raise LaunchUncertain("Cursor create outcome unknown; no automatic retry") from None

        if not isinstance(obj, dict):
            raise LaunchUncertain("Malformed Cursor create response")
        agent, run = obj.get("agent"), obj.get("run")
        if (not isinstance(agent, dict) or not isinstance(run, dict)
                or agent.get("id") != payload["agentId"]
                or run.get("agentId") != payload["agentId"]
                or not isinstance(run.get("id"), str)
                or not run["id"].startswith("run-")
                or run.get("status") not in ("CREATING", "RUNNING", "WAITING_FOR_BACKGROUND_WORK")):
            raise LaunchUncertain("Unverified new Cursor agent or run identity")
        return {"agent_id": agent["id"], "run_id": run["id"]}


def _result(state: str, reason: str, **fields: Any) -> dict[str, Any]:
    return {"state": state, "reason": reason, "launched": state == "STARTED",
            "automatic_merge": False, **fields}


def _start_one_locked(*, request_id: str, target_url: str,
                      proposal: dict[str, Any], permit: dict[str, Any],
                      controller: Controller, cursor_reader: Any,
                      cursor_create: Any, success_reason: str) -> dict[str, Any]:
    """One shared protected admission/POST transaction for PR and Issue origins."""
    if not _trusted_lease_ref_audit(controller):
        return _result("STOP", "lease_ref_exclusive_protection_unverified")
    inv = global_run_preflight(
        cursor_reader, global_account_scope_verified=permit["verified_account_scope"]
    )
    if inv.get("status") != "CLEAR":
        return _result("BUSY" if inv.get("status") == "BUSY" else "STOP",
                       "cursor_global_inventory_not_clear")
    try:
        acquired = controller.acquire(request_id, target_url)
    except LeaseError:
        return _result("STOP", "global_lease_unavailable")
    if acquired != "ACQUIRED":
        return _result("BUSY", "lease_" + acquired.lower())
    try:
        inv_again = global_run_preflight(
            cursor_reader, global_account_scope_verified=permit["verified_account_scope"]
        )
        if inv_again.get("status") != "CLEAR" or not _trusted_lease_ref_audit(controller):
            controller.transition(request_id, "RESERVED", "IDLE")
            return _result("STOP", "provider_or_ref_changed_after_lease")
        controller.transition(request_id, "RESERVED", "DISPATCHING")
    except LeaseError:
        return _result("STOP_LOCK_HELD", "lease_transition_unknown")
    # Never retry an ambiguous create, even if transport claims idempotence.
    try:
        created = cursor_create.create(proposal["payload"])
    except Exception:
        return _result("STOP_LOCK_HELD", "cursor_create_result_unknown",
                       agent_id=agent_id_for(request_id))
    try:
        if (not isinstance(created, dict)
                or created.get("agent_id") != agent_id_for(request_id)
                or not isinstance(created.get("run_id"), str)
                or not created["run_id"].startswith("run-")):
            return _result("STOP_LOCK_HELD", "cursor_returned_unknown_identity")
        controller.transition(
            request_id, "DISPATCHING", "RUNNING", run_id=created["run_id"]
        )
    except LeaseError:
        return _result("STOP_LOCK_HELD", "agent_started_but_lease_write_unknown",
                       agent_id=agent_id_for(request_id))
    return _result("STARTED", success_reason,
                   agent_id=created["agent_id"], run_id=created["run_id"],
                   work_url=target_url,
                   pr_url=target_url if "/pull/" in target_url else None)


def launch_single_approved_pr(*, request_id: str, bundle: dict[str, Any],
                              permit: dict[str, Any], controller: Controller,
                              cursor_reader: Any, cursor_create: Any) -> dict[str, Any]:
    """One run. No retries or next-task loop. Fails closed on any uncertainty.

    This function is inoperable in production while the code-level activation
    constant is False. Synthetic tests may monkeypatch the constant to test
    the transition logic WITHOUT making network calls.
    """
    if PILOT_ACTIVATION_ENABLED is not True:
        return _result("DISABLED", "owner_activation_not_enabled")
    if not isinstance(permit, dict):
        return _result("STOP", "permit_missing")
    required = (
        "verified_owner_approval", "verified_exact_scope",
        "verified_cursor_billing", "verified_external_billing_excluded",
        "verified_account_scope", "verified_launch_route_exclusivity",
        "verified_model_allowlist", "verified_subagents_disabled",
        "verified_owner_security_gates",
    )
    if any(permit.get(k) is not True for k in required):
        return _result("STOP", "trusted_owner_finance_or_scope_proof_missing")
    if permit.get("request_id") != request_id or not isinstance(
            permit.get("model_allowlist"), frozenset):
        return _result("STOP", "unverified_request_or_model_inventory")

    # Zero-model GitHub/semantic preflight, before touching provider or lock.
    recommendation = preview_one(bundle)
    if (recommendation.get("decision") != "REUSE_EXISTING_PR"
            or recommendation.get("launched") is not False
            or recommendation.get("execution_authorized") is not False
            or type(recommendation.get("selected_pr")) is not int):
        return _result("STOP", "integration_first_preview_not_approved")
    semantic = bundle["semantic"]
    repo = semantic["repository"]
    chosen = recommendation["selected_pr"]
    pr = next((x for x in semantic["prs"] if x["number"] == chosen), None)
    if pr is None:
        return _result("STOP", "missing_pr_selection")
    if (permit.get("repository") != repo or permit.get("pr_number") != chosen
            or permit.get("head_sha") != pr.get("head_sha")
            or permit.get("issue_number") != semantic["issue_number"]):
        return _result("STOP", "permit_does_not_match_fresh_pr")
    try:
        proposal = existing_pr_payload(
            request_id=request_id, repository=repo, pr_number=chosen,
            exact_pr_head=pr["head_sha"], issue_number=semantic["issue_number"],
            model_id=permit.get("model_id"),
            model_allowlist=permit["model_allowlist"],
        )
    except (ValueError, LeaseError):
        return _result("STOP", "cursor_payload_invalid")

    return _start_one_locked(
        request_id=request_id,
        target_url=proposal["payload"]["repos"][0]["prUrl"],
        proposal=proposal, permit=permit, controller=controller,
        cursor_reader=cursor_reader, cursor_create=cursor_create,
        success_reason="single_existing_pr_run_created",
    )


def launch_single_approved_issue(*, request_id: str, bundle: dict[str, Any],
                                 permit: dict[str, Any], controller: Controller,
                                 cursor_reader: Any, cursor_create: Any) -> dict[str, Any]:
    """One next-Issue run, using the SAME global lease and Cursor gateway.

    Requires BOTH accepted one-Issue preview and a separately attested accepted
    previous-merge handoff. Not a continuous-loop trigger or standing grant.
    Positive permit booleans must come from a future authenticated protected
    owner/domain runner, never raw Issue/user-controlled JSON. Code kill switch
    stays OFF in production.
    """
    if PILOT_ACTIVATION_ENABLED is not True:
        return _result("DISABLED", "owner_activation_not_enabled")
    if not isinstance(bundle, dict) or not isinstance(permit, dict):
        return _result("STOP", "issue_bundle_or_permit_missing")
    required = (
        "verified_owner_approval", "verified_exact_scope",
        "verified_cursor_billing", "verified_external_billing_excluded",
        "verified_account_scope", "verified_launch_route_exclusivity",
        "verified_model_allowlist", "verified_subagents_disabled",
        "verified_owner_security_gates",
    )
    if any(permit.get(k) is not True for k in required):
        return _result("STOP", "trusted_owner_finance_or_scope_proof_missing")
    if (permit.get("request_id") != request_id
            or not isinstance(permit.get("model_allowlist"), frozenset)):
        return _result("STOP", "unverified_request_or_model_inventory")
    preview = preview_one(bundle.get("preview"))
    handoff = preview_next_after_merge(bundle.get("handoff"))
    if (preview.get("decision") != "READY_FOR_OWNER_DISPATCH"
            or preview.get("execution_authorized") is not False
            or handoff.get("action") != "READY_FOR_OWNER_DISPATCH"
            or handoff.get("cursor_launch_authorized") is not False):
        return _result("STOP", "next_issue_preview_or_handoff_unverified")
    data = bundle["preview"]["semantic"]
    repo = data["repository"]
    issue_number = data["issue_number"]
    main_sha = data["default_sha"]
    proposed_paths = data.get("proposed_paths")
    queue = bundle["handoff"].get("queue")
    next_tasks = ([t for t in queue if isinstance(t, dict)
                   and t.get("number") == issue_number]
                  if isinstance(queue, list) else [])
    if (len(next_tasks) != 1
            or not isinstance(proposed_paths, list)
            or not isinstance(next_tasks[0].get("allowed_paths"), list)
            or sorted(proposed_paths) != sorted(next_tasks[0]["allowed_paths"])):
        return _result("STOP", "next_issue_file_scope_not_verified")
    if (bundle["handoff"].get("repository") != repo
            or handoff.get("next_issue_number") != issue_number
            or handoff.get("proposed_request_id") != request_id
            or bundle["handoff"].get("main", {}).get("before_sha") != main_sha
            or permit.get("repository") != repo
            or permit.get("issue_number") != issue_number
            or permit.get("head_sha") != main_sha
            or permit.get("proposed_request_id") != request_id):
        return _result("STOP", "next_issue_facts_do_not_match")
    try:
        proposal = single_issue_payload(
            request_id=request_id, repository=repo, issue_number=issue_number,
            exact_default_sha=main_sha, allowed_paths=proposed_paths,
            model_id=permit.get("model_id"),
            model_allowlist=permit["model_allowlist"],
        )
    except (ValueError, LeaseError):
        return _result("STOP", "new_issue_payload_invalid")
    url = f"https://github.com/{repo}/issues/{issue_number}"
    return _start_one_locked(
        request_id=request_id, target_url=url,
        proposal=proposal, permit=permit, controller=controller,
        cursor_reader=cursor_reader, cursor_create=cursor_create,
        success_reason="single_new_issue_run_created",
    )
