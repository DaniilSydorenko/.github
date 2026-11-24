#!/usr/bin/env python3
"""#164 protected live pipeline wiring (Issues #216–#226).

Composes vertical pregates with parameterized executor, Draft PR publisher, and
exact-head CI evidence gates. Model spend and GitHub mutation require protected
workflow authority, explicit live attestation, and per-issue owner GO.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from github_ref_lease import Controller
from openhands_164_draft_publisher import _PROTECTED_AUTHORITY as PUBLISHER_AUTHORITY
from openhands_164_draft_publisher import publish_verified_patch
from openhands_164_executor import MODEL_DEFAULT
from openhands_164_executor import _TRUSTED_AUTHORIZATION as EXECUTOR_AUTHORITY
from openhands_164_executor import execute_authorized, validate_workspace
from openhands_164_issue_preflight import evaluate_issue_satisfaction
from openhands_164_patch_contract import ALLOWED, PatchContractError, prepare_verified_patch, verify_workspace_change
from openhands_164_publisher_handoff import verify_patch_for_handoff
from openhands_164_vertical_integration import (
    TERMINAL_OFFLINE,
    CiEvidence,
    VerticalRequest,
    run_offline_vertical,
    run_vertical_pregates,
)
from openhands_lease_admission_adapter import (
    LeaseRefEvidence,
    RulesetEvidence,
    TargetHeadEvidence,
    WriterIdentityEvidence,
    request_id_for,
)
from openhands_runner_admission_bridge import (
    ProviderBudgetAttestation,
    TrustedWorkflowAttestation,
    evaluate_before_model_handoff,
)
from github_ref_lease import agent_id_for

SHA = re.compile(r"[0-9a-f]{40}\Z")
CONTROL_REPO = "DaniilSydorenko/.github"
CONTROL_ACTOR = "DaniilSydorenko"
APPROVED_OPERATION = "pilot-live-164-execute"
TERMINAL_WIRED = "live_164_vertical_wiring_verified_owner_gated"
TERMINAL_PUBLISHED = "live_164_draft_pr_published_pending_ci"
TERMINAL_CI_VERIFIED = "live_164_pilot_complete_ci_verified"
_PRE_MODEL_OK = frozenset({"model_handoff_blocked_live_capability_unverified"})


@dataclass(frozen=True)
class ProtectedWorkflowContext:
    """Workflow-injected dispatch context; never parse from issue text or PR body."""

    repository: str
    actor: str
    ref: str
    event_name: str
    run_attempt: str
    operation: str
    owner_go_issue: int | None


@dataclass(frozen=True)
class LiveWiringRequest:
    issue: int
    workflow_run_id: str
    inventory: Mapping[str, Any]
    trusted: TrustedWorkflowAttestation | None
    budget: ProviderBudgetAttestation | None
    protected: ProtectedWorkflowContext | None
    prior_proofs: Sequence[Any] = ()
    open_prs_for_target: Sequence[int] = ()
    ci_after_publish: CiEvidence | None = None


@dataclass(frozen=True)
class LiveExecutionConfig:
    """Trusted workflow-only live execution attestation; never from issue text."""

    live_attested: bool
    api_key: str | None = None
    model: str = MODEL_DEFAULT
    publisher_token: str | None = None


def _stop(reason: str, **extra: Any) -> dict[str, Any]:
    base = {
        "decision": "STOP",
        "reason": reason,
        "model_invoked": False,
        "github_write": False,
        "publish_authorized": False,
        "live_openhands_authorized": False,
    }
    base.update(extra)
    return base


def build_trusted_workflow_attestation(
    lease_store,
    issue: int,
    target_head_sha: str,
    *, ruleset: RulesetEvidence | None = None,
    rechecked_head_sha: str | None = None,
) -> TrustedWorkflowAttestation:
    """Construct workflow-injected attestation from an authenticated lease snapshot."""
    rid = request_id_for(issue)
    snap = lease_store.read()
    writer = agent_id_for(rid)
    head = snap.sha
    return TrustedWorkflowAttestation(
        expected_lease_sha=head,
        lease=LeaseRefEvidence(
            observed_ref_head_sha=head,
            snapshot_commit_sha=head,
            state=snap.state,
            authenticated_ref=True,
            exclusive_writer_verified=True,
            credential_path_verified=True,
        ),
        target_head=TargetHeadEvidence(target_head_sha, target_head_sha, rechecked_head_sha or "", rechecked_head_sha is not None),
        writer=WriterIdentityEvidence(writer, True),
        ruleset=ruleset,
    )


def protected_context_from_env() -> ProtectedWorkflowContext | None:
    keys = (
        "GITHUB_REPOSITORY",
        "GITHUB_ACTOR",
        "GITHUB_REF",
        "GITHUB_EVENT_NAME",
        "GITHUB_RUN_ATTEMPT",
        "AI_ENG_APPROVED_OPERATION",
        "AI_ENG_OWNER_GO_ISSUE",
    )
    if any(os.environ.get(k) in (None, "") for k in keys):
        return None
    raw_issue = os.environ.get("AI_ENG_OWNER_GO_ISSUE", "")
    owner_go_issue = None
    if raw_issue.isdigit():
        owner_go_issue = int(raw_issue)
    return ProtectedWorkflowContext(
        repository=os.environ["GITHUB_REPOSITORY"],
        actor=os.environ["GITHUB_ACTOR"],
        ref=os.environ["GITHUB_REF"],
        event_name=os.environ["GITHUB_EVENT_NAME"],
        run_attempt=os.environ["GITHUB_RUN_ATTEMPT"],
        operation=os.environ["AI_ENG_APPROVED_OPERATION"],
        owner_go_issue=owner_go_issue,
    )


def evaluate_ci_evidence(ci: CiEvidence | None) -> dict[str, Any] | None:
    if ci is None:
        return _stop("ci_evidence_missing")
    if ci.aggregate in ("PENDING", "UNKNOWN", "SKIPPED", None):
        return _stop("ci_aggregate_incomplete", aggregate=ci.aggregate)
    if ci.security in ("PENDING", "UNKNOWN", "SKIPPED", None):
        return _stop("ci_security_incomplete", security=ci.security)
    if not ci.verified():
        return _stop("ci_evidence_failed", aggregate=ci.aggregate, security=ci.security)
    return None


def verify_protected_context(ctx: ProtectedWorkflowContext, issue: int) -> dict[str, Any] | None:
    if ctx.repository != CONTROL_REPO:
        return _stop("wrong_control_repository")
    if ctx.actor != CONTROL_ACTOR:
        return _stop("wrong_actor")
    if ctx.ref != "refs/heads/main":
        return _stop("wrong_control_ref")
    if ctx.event_name != "workflow_dispatch":
        return _stop("not_manual_dispatch")
    if ctx.run_attempt != "1":
        return _stop("rerun_disallowed")
    if ctx.operation != APPROVED_OPERATION:
        return _stop("wrong_operation")
    if ctx.owner_go_issue != issue:
        return _stop("owner_go_issue_mismatch", expected=issue, got=ctx.owner_go_issue)
    return None


def _release_lease_without_spend(lease_store, request_id: str) -> None:
    controller = Controller(lease_store)
    try:
        controller.transition(request_id, "RESERVED", "IDLE")
    except Exception:
        pass


def _complete_patch_pipeline(
    workspace: pathlib.Path,
    base_sha: str,
    issue: int,
) -> tuple[dict[str, Any] | None, pathlib.Path | None]:
    try:
        patch_verdict = verify_workspace_change(workspace, base_sha, issue)
    except (PatchContractError, OSError, ValueError) as exc:
        return _stop("patch_scope_unverified", detail=str(exc)), None
    if patch_verdict.get("decision") != "PATCH_SCOPE_VERIFIED":
        return _stop("patch_scope_unverified"), None

    tmp = tempfile.TemporaryDirectory()
    patch_file = pathlib.Path(tmp.name) / f"issue-{issue}.patch"
    clean = pathlib.Path(tmp.name) / "clean-checkout"
    try:
        prepare_verified_patch(workspace, base_sha, issue, patch_file)
        subprocess.run(
            ["git", "clone", "-q", "--no-hardlinks", str(workspace), str(clean)],
            check=True,
            timeout=30,
        )
        subprocess.run(
            ["git", "-C", str(clean), "checkout", "-q", base_sha],
            check=True,
            timeout=15,
        )
        handoff = verify_patch_for_handoff(clean, base_sha, issue, patch_file)
    except (PatchContractError, OSError, subprocess.SubprocessError) as exc:
        tmp.cleanup()
        return _stop("publisher_handoff_rejected", detail=str(exc)), None
    if handoff.get("decision") != "READY_FOR_PROTECTED_PUBLISHER_REVIEW":
        tmp.cleanup()
        return _stop("publisher_handoff_not_ready"), None
    return None, pathlib.Path(workspace) / ALLOWED[issue]


def run_protected_live_wiring(
    request: LiveWiringRequest,
    *,
    lease_store,
    workspace,
    base_sha: str,
    wiring_mode: str = "offline_replay",
    live_config: LiveExecutionConfig | None = None,
    apply_agent_change: Callable | None = None,
    executor=execute_authorized,
    publisher=publish_verified_patch,
    publisher_transport=None,
    protected_authority=EXECUTOR_AUTHORITY,
    publisher_authority=PUBLISHER_AUTHORITY,
) -> dict[str, Any]:
    issue = request.issue
    if type(issue) is not int or issue not in ALLOWED:
        return _stop("unexpected_issue")
    if not isinstance(base_sha, str) or not SHA.fullmatch(base_sha):
        return _stop("invalid_base_sha")
    root = pathlib.Path(workspace).resolve()

    if wiring_mode == "offline_replay":
        vertical = run_offline_vertical(
            VerticalRequest(
                issue,
                request.workflow_run_id,
                request.inventory,
                trusted=request.trusted,
                budget=request.budget,
                prior_proofs=request.prior_proofs,
                open_prs_for_target=request.open_prs_for_target,
                ci_after_publish=request.ci_after_publish,
            ),
            lease_store=lease_store,
            workspace=root,
            base_sha=base_sha,
            apply_agent_change=apply_agent_change,
        )
        if vertical.get("reason") != TERMINAL_OFFLINE:
            return vertical
        if not vertical.get("publisher_handoff_ready"):
            return _stop("publisher_handoff_not_ready")
    else:
        pre = run_vertical_pregates(
            VerticalRequest(
                issue,
                request.workflow_run_id,
                request.inventory,
                trusted=request.trusted,
                budget=request.budget,
                prior_proofs=request.prior_proofs,
                open_prs_for_target=request.open_prs_for_target,
            ),
            lease_store=lease_store,
            base_sha=base_sha,
        )
        if pre.get("decision") != "PREGATES_PASS":
            return pre

    admission = evaluate_before_model_handoff(
        issue,
        request.workflow_run_id,
        trusted_attestation=request.trusted,
        budget_attestation=request.budget,
    )
    if admission.get("decision") != "STOP":
        return _stop("admission_not_fail_closed", admission=admission)
    if admission.get("reason") not in _PRE_MODEL_OK:
        return _stop(admission.get("reason", "admission_denied"))

    ctx = request.protected
    if ctx is None:
        return _stop(
            "protected_workflow_context_missing",
            wiring_stage="pre_executor",
            patch_scope_verified=wiring_mode == "offline_replay",
            publisher_handoff_ready=wiring_mode == "offline_replay",
        )
    denied = verify_protected_context(ctx, issue)
    if denied is not None:
        return denied

    if protected_authority is not EXECUTOR_AUTHORITY:
        return _stop("executor_authority_missing", wiring_stage="pre_model")
    if publisher_authority is not PUBLISHER_AUTHORITY:
        return _stop("publisher_authority_missing", wiring_stage="pre_publish")

    if wiring_mode == "offline_replay":
        return _stop(
            TERMINAL_WIRED,
            issue=issue,
            target=ALLOWED[issue],
            base_sha=base_sha,
            patch_scope_verified=True,
            publisher_handoff_ready=True,
            admission_reason=admission.get("reason"),
            executor_ready=executor is execute_authorized,
            publisher_ready=publisher is publish_verified_patch,
            model_invoked=False,
            github_write=False,
            publish_authorized=False,
            live_openhands_authorized=False,
        )

    satisfaction = evaluate_issue_satisfaction(issue, root)
    if satisfaction.get("reason") == "ALREADY_SATISFIED":
        _release_lease_without_spend(lease_store, request_id_for(issue))
        return {**satisfaction, "base_sha": base_sha, "publish_authorized": False}

    config = live_config or LiveExecutionConfig(live_attested=False)
    if not config.live_attested:
        return _stop(
            TERMINAL_WIRED,
            issue=issue,
            target=ALLOWED[issue],
            base_sha=base_sha,
            patch_scope_verified=False,
            publisher_handoff_ready=False,
            admission_reason=admission.get("reason"),
            live_execute_path=True,
            model_invoked=False,
            github_write=False,
            publish_authorized=False,
            live_openhands_authorized=False,
        )

    if not config.api_key:
        return _stop("live_api_key_missing")
    if not config.publisher_token:
        return _stop("live_publisher_token_missing")

    rid = request_id_for(issue)
    controller = Controller(lease_store)
    try:
        controller.transition(rid, "RESERVED", "DISPATCHING")
        controller.transition(rid, "DISPATCHING", "RUNNING", run_id=f"run-{request.workflow_run_id}")
    except Exception as exc:
        return _stop("lease_transition_failed", detail=type(exc).__name__)

    model_invoked = False
    try:
        validated = validate_workspace(root, issue, base_sha=base_sha)
        executor(validated, config.api_key, config.model, issue, authorization=protected_authority)
        model_invoked = True
    except (PermissionError, ValueError, RuntimeError, OSError) as exc:
        try:
            controller.transition(rid, "RUNNING", "BLOCKED")
            lease_phase = "BLOCKED"
        except Exception:
            lease_phase = "RUNNING"
        return _stop(
            "executor_failed",
            detail=type(exc).__name__,
            model_invoked=model_invoked,
            lease_phase=lease_phase,
        )

    denied_patch, content_path = _complete_patch_pipeline(root, base_sha, issue)
    if denied_patch is not None:
        try:
            controller.transition(rid, "RUNNING", "BLOCKED")
            denied_patch = {**denied_patch, "lease_phase": "BLOCKED"}
        except Exception:
            denied_patch = {**denied_patch, "lease_phase": "RUNNING"}
        return {**denied_patch, "model_invoked": model_invoked}

    assert content_path is not None
    if publisher_transport is None:
        return _stop("publisher_transport_missing", model_invoked=model_invoked)

    try:
        pr = publisher(
            issue=issue,
            token=config.publisher_token,
            base_sha=base_sha,
            content_path=content_path,
            authority=publisher_authority,
            transport=publisher_transport,
        )
    except (PermissionError, ValueError, RuntimeError) as exc:
        try:
            controller.transition(rid, "RUNNING", "BLOCKED")
            lease_phase = "BLOCKED"
        except Exception:
            lease_phase = "RUNNING"
        return _stop(
            "publisher_failed",
            detail=type(exc).__name__,
            model_invoked=model_invoked,
            lease_phase=lease_phase,
        )

    pr_url = pr.get("html_url") if isinstance(pr, dict) else None
    if not isinstance(pr_url, str) or not pr_url.startswith("https://"):
        return _stop("publisher_missing_pr_url", model_invoked=model_invoked)

    try:
        controller.transition(rid, "RUNNING", "VERIFYING")
        controller.bind_generated_pr(
            rid,
            expected_issue_url=f"https://github.com/DaniilSydorenko/haversine-geolocation/issues/{issue}",
            generated_pr_url=pr_url,
        )
    except Exception as exc:
        return _stop("lease_bind_failed", detail=type(exc).__name__, model_invoked=True, pr_url=pr_url)

    result = {
        "decision": "STOP",
        "reason": TERMINAL_PUBLISHED,
        "issue": issue,
        "target": ALLOWED[issue],
        "base_sha": base_sha,
        "pr_url": pr_url,
        "patch_scope_verified": True,
        "model_invoked": True,
        "github_write": True,
        "publish_authorized": True,
        "live_openhands_authorized": True,
        "ci_verified": False,
        "pilot_complete": False,
        "lease_phase": "VERIFYING",
        "lease_handoff": "durable_until_owner_ci_and_release",
    }

    if request.ci_after_publish is not None:
        ci_denied = evaluate_ci_evidence(request.ci_after_publish)
        if ci_denied is not None:
            return {**result, **ci_denied, "pr_url": pr_url, "model_invoked": True, "github_write": True}

    if request.ci_after_publish is not None and request.ci_after_publish.verified():
        try:
            controller.release_verified(
                rid,
                provider_terminal=True,
                integration_accepted=False,
                manual_approval=True,
            )
        except Exception as exc:
            return _stop("lease_release_failed", detail=type(exc).__name__, pr_url=pr_url, model_invoked=True)
        result["reason"] = TERMINAL_CI_VERIFIED
        result["ci_aggregate"] = request.ci_after_publish.aggregate
        result["ci_security"] = request.ci_after_publish.security

    return result


def self_test() -> None:
    import pathlib
    import subprocess
    import tempfile

    from test_github_ref_lease import MemoryGitRef
    from test_openhands_runner_admission_bridge import BUDGET_OK, trusted_bundle

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / "repo"
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(
            ["git", "-C", str(root), "-c", "user.name=Test", "-c",
             "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "base"],
            check=True,
        )
        sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        inventory = {
            "reason": "live_authorization_not_integrated",
            "default_head": sha,
            "issues": [{"number": n, "target": p} for n, p in ((216, ALLOWED[216]), (217, ALLOWED[217]), (226, ALLOWED[226]))],
        }

        def write_doc(ws: pathlib.Path, issue: int) -> None:
            path = ws / ALLOWED[issue]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("compatibility notes\n", encoding="utf-8")

        store_a = MemoryGitRef()
        out = run_protected_live_wiring(
            LiveWiringRequest(216, "9001", inventory, trusted=trusted_bundle(store_a), budget=BUDGET_OK, protected=None),
            lease_store=store_a,
            workspace=root,
            base_sha=sha,
            apply_agent_change=write_doc,
        )
        assert out["reason"] == "protected_workflow_context_missing"
        assert out["patch_scope_verified"]

        ctx = ProtectedWorkflowContext(
            CONTROL_REPO, CONTROL_ACTOR, "refs/heads/main", "workflow_dispatch", "1",
            APPROVED_OPERATION, 216,
        )
        store_b = MemoryGitRef()
        wired = run_protected_live_wiring(
            LiveWiringRequest(216, "9002", inventory, trusted=trusted_bundle(store_b), budget=BUDGET_OK, protected=ctx),
            lease_store=store_b,
            workspace=root,
            base_sha=sha,
            apply_agent_change=write_doc,
        )
        assert wired["reason"] == TERMINAL_WIRED
        assert wired["patch_scope_verified"] and not wired["model_invoked"]

    print("PASS: #164 protected live wiring offline self-test")


if __name__ == "__main__":
    self_test()