#!/usr/bin/env python3
"""#164 offline vertical chain: inventory → lease → admission → patch → publisher STOP.

Wires existing modules into one deterministic orchestrator for Issues #216,
#217, and #226. No model calls, provider spend, lease mutation in tests that
inject MemoryGitRef without acquire, or GitHub writes unless an explicit mock
publisher is supplied for idempotency drills.

Live owner-triggered execution remains blocked until separate workflow wiring
and owner GO; a successful offline run ends with
``offline_vertical_chain_verified_live_publish_blocked``.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from github_ref_lease import Controller
from openhands_164_patch_contract import ALLOWED, PatchContractError, prepare_verified_patch, verify_workspace_change
from openhands_164_publisher_handoff import verify_patch_for_handoff
from openhands_164_sequential_handoff import IssueProof, next_issue
from openhands_live_orchestrator import EXPECTED
from openhands_runner_admission_bridge import (
    ProviderBudgetAttestation,
    TrustedWorkflowAttestation,
    evaluate_before_model_handoff,
)
from openhands_lease_admission_adapter import request_id_for

SHA = re.compile(r"[0-9a-f]{40}\Z")
INVENTORY_OK = "live_authorization_not_integrated"
TERMINAL_OFFLINE = "offline_vertical_chain_verified_live_publish_blocked"
_PRE_EXECUTOR_ADMISSION = frozenset({
    "model_handoff_blocked_live_capability_unverified",
})


@dataclass(frozen=True)
class CiEvidence:
    aggregate: str
    security: str

    def verified(self) -> bool:
        return self.aggregate == "SUCCESS" and self.security == "SUCCESS"


@dataclass(frozen=True)
class VerticalRequest:
    issue: int
    workflow_run_id: str
    inventory: Mapping[str, Any]
    trusted: TrustedWorkflowAttestation | None
    budget: ProviderBudgetAttestation | None
    prior_proofs: Sequence[IssueProof] = ()
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


def _validate_inventory(inventory: Mapping[str, Any], issue: int) -> dict[str, Any] | None:
    if inventory.get("reason") != INVENTORY_OK:
        return _stop("inventory_not_verified")
    head = inventory.get("default_head")
    if not isinstance(head, str) or not SHA.fullmatch(head):
        return _stop("default_head_unverified")
    expected_issues = [{"number": n, "target": p} for n, p in EXPECTED]
    if inventory.get("issues") != expected_issues:
        return _stop("queue_mismatch")
    if issue not in ALLOWED:
        return _stop("unexpected_issue")
    return None


def _sequential_gate(issue: int, proofs: Sequence[IssueProof]) -> dict[str, Any] | None:
    slot = next_issue(tuple(proofs))
    if slot.get("reason") != "next_issue_candidate_not_live_authorization":
        return _stop(slot.get("reason", "sequential_gate_denied"))
    if slot.get("next_issue") != issue:
        return _stop("sequential_issue_not_eligible", expected=slot.get("next_issue"))
    return None


def _collision_gate(issue: int, open_prs: Sequence[int]) -> dict[str, Any] | None:
    if open_prs:
        return _stop("duplicate_or_overlapping_pr", issue=issue, open_prs=list(open_prs))
    return None


def publisher_precheck(*, base_sha: str, issue: int, existing_branch_pr: bool) -> dict[str, Any]:
    if not SHA.fullmatch(base_sha):
        return _stop("invalid_base_sha")
    if issue not in ALLOWED:
        return _stop("unexpected_issue")
    if existing_branch_pr:
        return _stop("duplicate_pr_for_issue_branch")
    return {"decision": "PRECHECK_PASS", "issue": issue, "base_sha": base_sha}


def run_vertical_pregates(request: VerticalRequest, *, lease_store, base_sha: str) -> dict[str, Any]:
    """Inventory through exclusive lease and admission; stops before agent execution."""
    issue = request.issue
    if type(issue) is not int or issue not in ALLOWED:
        return _stop("unexpected_issue")

    for gate in (
        lambda: _validate_inventory(request.inventory, issue),
        lambda: _sequential_gate(issue, request.prior_proofs),
        lambda: _collision_gate(issue, request.open_prs_for_target),
    ):
        denied = gate()
        if denied is not None:
            return denied

    head = request.inventory["default_head"]
    if base_sha != head:
        return _stop("base_sha_mismatch", inventory_head=head, workspace_base=base_sha)

    rid = request_id_for(issue)
    lease = Controller(lease_store)
    acquired = lease.acquire(rid, f"https://github.com/DaniilSydorenko/haversine-geolocation/issues/{issue}")
    if acquired not in ("ACQUIRED", "ALREADY_OWNED"):
        return _stop("lease_contention", lease_outcome=acquired, request_id=rid)

    trusted = request.trusted
    if trusted is None:
        return _stop("missing_trusted_workflow_attestation")

    admission = evaluate_before_model_handoff(
        issue,
        request.workflow_run_id,
        trusted_attestation=trusted,
        budget_attestation=request.budget,
    )
    if admission.get("decision") != "STOP":
        return _stop("admission_not_fail_closed", admission=admission)
    if admission.get("reason") not in _PRE_EXECUTOR_ADMISSION:
        return _stop(admission.get("reason", "admission_denied"))

    precheck = publisher_precheck(
        base_sha=base_sha,
        issue=issue,
        existing_branch_pr=bool(request.open_prs_for_target),
    )
    if precheck.get("decision") != "PRECHECK_PASS":
        return precheck

    return {
        "decision": "PREGATES_PASS",
        "issue": issue,
        "target": ALLOWED[issue],
        "base_sha": base_sha,
        "request_id": rid,
        "admission_reason": admission.get("reason"),
        "lease_outcome": acquired,
        "model_invoked": False,
        "github_write": False,
        "publish_authorized": False,
        "live_openhands_authorized": False,
    }


def run_offline_vertical(
    request: VerticalRequest,
    *,
    lease_store,
    workspace: pathlib.Path,
    base_sha: str,
    apply_agent_change: Callable[[pathlib.Path, int], None] | None = None,
) -> dict[str, Any]:
    """Execute the wired chain without live OpenHands or GitHub mutation."""
    issue = request.issue
    if type(issue) is not int or issue not in ALLOWED:
        return _stop("unexpected_issue")

    pre = run_vertical_pregates(request, lease_store=lease_store, base_sha=base_sha)
    if pre.get("decision") != "PREGATES_PASS":
        return pre
    admission_reason = pre.get("admission_reason", "model_handoff_blocked")

    if apply_agent_change is None:
        return _stop(
            admission_reason,
            stage="pre_executor",
            patch_scope_verified=False,
        )

    try:
        apply_agent_change(workspace, issue)
        patch_verdict = verify_workspace_change(workspace, base_sha, issue)
    except (PatchContractError, OSError, ValueError) as exc:
        return _stop("patch_scope_unverified", detail=str(exc))

    if patch_verdict.get("decision") != "PATCH_SCOPE_VERIFIED":
        return _stop("patch_scope_unverified")

    with tempfile.TemporaryDirectory() as tmp:
        patch_file = pathlib.Path(tmp) / f"issue-{issue}.patch"
        clean = pathlib.Path(tmp) / "clean-checkout"
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
            return _stop("publisher_handoff_rejected", detail=str(exc))

    precheck = publisher_precheck(
        base_sha=base_sha,
        issue=issue,
        existing_branch_pr=bool(request.open_prs_for_target),
    )
    if precheck.get("decision") != "PRECHECK_PASS":
        return precheck

    if request.ci_after_publish is not None and not request.ci_after_publish.verified():
        agg = request.ci_after_publish.aggregate
        sec = request.ci_after_publish.security
        if agg in ("PENDING", "UNKNOWN", "SKIPPED", None) or sec in ("PENDING", "UNKNOWN", "SKIPPED", None):
            return _stop("ci_evidence_incomplete", aggregate=agg, security=sec)
        return _stop("ci_evidence_failed", aggregate=agg, security=sec)

    return {
        "decision": "STOP",
        "reason": TERMINAL_OFFLINE,
        "issue": issue,
        "target": ALLOWED[issue],
        "base_sha": base_sha,
        "patch_scope_verified": True,
        "publisher_handoff_ready": handoff.get("decision") == "READY_FOR_PROTECTED_PUBLISHER_REVIEW",
        "admission_reason": admission_reason,
        "model_invoked": False,
        "github_write": False,
        "publish_authorized": False,
        "live_openhands_authorized": False,
    }


def self_test() -> None:
    import subprocess
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
            "reason": INVENTORY_OK,
            "default_head": sha,
            "issues": [{"number": n, "target": p} for n, p in EXPECTED],
        }

        def write_doc(ws: pathlib.Path, issue: int) -> None:
            path = ws / ALLOWED[issue]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("grounded pilot documentation\n", encoding="utf-8")

        store = MemoryGitRef()
        req = VerticalRequest(
            216, "888001", inventory,
            trusted=trusted_bundle(store), budget=BUDGET_OK,
        )
        out = run_offline_vertical(req, lease_store=store, workspace=root, base_sha=sha, apply_agent_change=write_doc)
        assert out["reason"] == TERMINAL_OFFLINE and out["patch_scope_verified"]
        assert not out["github_write"] and not out["model_invoked"]

        store2 = MemoryGitRef()
        trusted_a = trusted_bundle(store2)
        Controller(store2).acquire(
            request_id_for(216),
            "https://github.com/DaniilSydorenko/haversine-geolocation/issues/216",
        )
        store2_b = MemoryGitRef()
        out_busy = run_offline_vertical(
            VerticalRequest(217, "888002", inventory, trusted=trusted_bundle(store2_b, issue=217), budget=BUDGET_OK),
            lease_store=store2_b, workspace=root, base_sha=sha, apply_agent_change=write_doc,
        )
        assert out_busy["reason"] == "sequential_issue_not_eligible"

        dup = run_offline_vertical(
            VerticalRequest(216, "888003", inventory, trusted=trusted_a, budget=BUDGET_OK, open_prs_for_target=[999]),
            lease_store=MemoryGitRef(), workspace=root, base_sha=sha, apply_agent_change=write_doc,
        )
        assert dup["reason"] == "duplicate_or_overlapping_pr"

    print("PASS: #164 offline vertical integration self-test")


if __name__ == "__main__":
    self_test()