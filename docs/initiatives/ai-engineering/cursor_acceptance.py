"""Independent integration eligibility of a bound Cursor PR (read-only).

Quality evidence is the target repository's own required CI on the EXACT
head (for Haversine "Test and build" runs npm quality/typecheck/test/build on
an unprivileged GitHub runner; this process never runs candidate code and holds
no candidate checkout). Passing CI is not semantic acceptance: the owner's
latest review on the exact head must be APPROVED. The executor cannot approve
its own PR and nothing here merges.
"""
from __future__ import annotations

from typing import Any

from cursor_bundle_builder import check_runs_at, owner_approved_at, required_checks_state
from cursor_pr_binding import pr_files
from cursor_tasks import OWNER, CursorTask

ELIGIBLE = "INTEGRATION_ELIGIBLE"


def evaluate(gh: Any, task: CursorTask, *, pr_number: int, bound_head_sha: str) -> dict[str, Any]:
    """Status: INTEGRATED | INTEGRATION_ELIGIBLE | PENDING_CI | PENDING_REVIEW |
    REJECTED | STOP. Every status except INTEGRATED keeps the lease."""
    pr = gh.get_json(f"/repos/{task.repository}/pulls/{pr_number}")
    if not isinstance(pr, dict):
        return {"status": "STOP", "reason": "pr_unreadable"}
    head = (pr.get("head") or {}).get("sha")
    if head != bound_head_sha:
        # Any push after binding needs a fresh owner decision; old evidence never carries over.
        return {"status": "STOP", "reason": "pr_head_moved_after_binding",
                "bound_head": bound_head_sha, "observed_head": head}
    if pr.get("state") == "closed" and pr.get("merged") is not True:
        return {"status": "REJECTED", "reason": "pr_closed_without_merge"}

    files = pr_files(gh, task.repository, pr_number)
    if files is None:
        return {"status": "STOP", "reason": "pr_file_inventory_incomplete"}
    outside = sorted(set(files) - set(task.allowed_paths))
    if outside or not files:
        return {"status": "REJECTED", "reason": "pr_scope_violation", "paths": outside}

    runs = check_runs_at(gh, task.repository, head)
    if runs is None:
        return {"status": "STOP", "reason": "check_run_inventory_incomplete"}
    ci = required_checks_state(runs, task.required_checks)
    approved = owner_approved_at(gh, task.repository, pr_number, head)
    evidence = {"exact_head": head, "required_checks": list(task.required_checks),
                "ci": ci, "owner_approved_exact_head": approved, "files": sorted(set(files))}
    if pr.get("merged") is True:
        merged_by = (pr.get("merged_by") or {}).get("login")
        if ci == "SUCCESS" and approved and merged_by == OWNER:
            return {"status": "INTEGRATED", "reason": "owner_merged_verified_head",
                    "merge_sha": pr.get("merge_commit_sha"), **evidence}
        return {"status": "STOP", "reason": "merged_without_complete_evidence",
                "merged_by": merged_by, **evidence}
    if ci == "FAILURE":
        return {"status": "REJECTED", "reason": "required_ci_failed", **evidence}
    if ci != "SUCCESS":
        return {"status": "PENDING_CI", "reason": "required_ci_pending", **evidence}
    if not approved:
        return {"status": "PENDING_REVIEW", "reason": "owner_semantic_review_required", **evidence}
    return {"status": ELIGIBLE, "reason": "ready_for_owner_merge", **evidence}
