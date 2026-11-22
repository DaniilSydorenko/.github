#!/usr/bin/env python3
"""#164 protected live pipeline wiring (Issues #216–#226).

Composes offline vertical integration with parameterized executor, Draft PR
publisher, and exact-head CI evidence gates. This module never authorizes model
spend or GitHub mutation unless the protected workflow injects authority and an
explicit per-issue owner GO; coding-session and default paths remain STOP.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from openhands_164_draft_publisher import _PROTECTED_AUTHORITY as PUBLISHER_AUTHORITY
from openhands_164_draft_publisher import publish_verified_patch
from openhands_164_executor import _TRUSTED_AUTHORIZATION as EXECUTOR_AUTHORITY
from openhands_164_executor import execute_authorized
from openhands_164_patch_contract import ALLOWED
from openhands_164_vertical_integration import (
    TERMINAL_OFFLINE,
    CiEvidence,
    VerticalRequest,
    run_offline_vertical,
)
from openhands_runner_admission_bridge import (
    ProviderBudgetAttestation,
    TrustedWorkflowAttestation,
    evaluate_before_model_handoff,
)

SHA = re.compile(r"[0-9a-f]{40}\Z")
CONTROL_REPO = "DaniilSydorenko/.github"
CONTROL_ACTOR = "DaniilSydorenko"
APPROVED_OPERATION = "pilot-live-164-execute"
TERMINAL_WIRED = "live_164_vertical_wiring_verified_owner_gated"
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


def run_protected_live_wiring(
    request: LiveWiringRequest,
    *,
    lease_store,
    workspace,
    base_sha: str,
    apply_agent_change: Callable | None = None,
    executor=execute_authorized,
    publisher=publish_verified_patch,
    publisher_transport=None,
    publisher_token: str | None = None,
    protected_authority=EXECUTOR_AUTHORITY,
    publisher_authority=PUBLISHER_AUTHORITY,
) -> dict[str, Any]:
    issue = request.issue
    if type(issue) is not int or issue not in ALLOWED:
        return _stop("unexpected_issue")
    if not isinstance(base_sha, str) or not SHA.fullmatch(base_sha):
        return _stop("invalid_base_sha")

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
        workspace=workspace,
        base_sha=base_sha,
        apply_agent_change=apply_agent_change,
    )
    if vertical.get("reason") != TERMINAL_OFFLINE:
        return vertical
    if not vertical.get("publisher_handoff_ready"):
        return _stop("publisher_handoff_not_ready")

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
            patch_scope_verified=True,
            publisher_handoff_ready=True,
        )
    denied = verify_protected_context(ctx, issue)
    if denied is not None:
        return denied

    if protected_authority is not EXECUTOR_AUTHORITY:
        return _stop("executor_authority_missing", wiring_stage="pre_model")

    # Owner GO and workflow attestations are present; still no model in offline wiring.
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
        assert out["publisher_handoff_ready"]

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