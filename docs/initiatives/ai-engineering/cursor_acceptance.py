"""Independent integration eligibility of a bound Cursor PR (read-only).

Quality evidence is the target repository's own required CI on the EXACT
head (for Haversine "Test and build" runs npm quality/typecheck/test/build on
an unprivileged GitHub runner; this process never runs candidate code and holds
no candidate checkout). Nothing here merges.

Semantic acceptance is the owner's own merge of the exact bound head. Cursor
Cloud Agent PRs are opened under the owner's GitHub account, and GitHub never
lets a PR author approve their own PR, so an owner APPROVED review cannot be
required. INTEGRATION_ELIGIBLE only means "ready for the owner to review and
merge"; only INTEGRATED (owner merge of the bound head, green required CI on
that head, merge commit on the default branch) releases the lease.
"""
from __future__ import annotations

import re
from typing import Any

from cursor_bundle_builder import check_runs_at, owner_approved_at, required_checks_state
from cursor_pr_binding import pr_files
from cursor_tasks import OWNER, CursorTask

ELIGIBLE = "INTEGRATION_ELIGIBLE"
SHA = re.compile(r"[0-9a-f]{40}\Z")


def merge_on_default(gh: Any, task: CursorTask, merge_sha: Any) -> bool:
    """The merge commit is reachable from the task's default branch."""
    if not (isinstance(merge_sha, str) and SHA.fullmatch(merge_sha)):
        return False
    compare = gh.get_json(f"/repos/{task.repository}/compare/{merge_sha}...{task.default_branch}")
    return (isinstance(compare, dict) and compare.get("status") in ("ahead", "identical")
            and compare.get("behind_by") == 0)


def evaluate(gh: Any, task: CursorTask, *, pr_number: int, bound_head_sha: str) -> dict[str, Any]:
    """Status: INTEGRATED | INTEGRATION_ELIGIBLE | PENDING_CI | REJECTED | STOP.
    Every status except INTEGRATED keeps the lease."""
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
    evidence = {"exact_head": head, "required_checks": list(task.required_checks),
                "ci": ci, "files": sorted(set(files)),
                # Informational only: impossible when the owner authored the PR.
                "owner_approved_exact_head": owner_approved_at(gh, task.repository,
                                                               pr_number, head)}
    if pr.get("merged") is True:
        merged_by = (pr.get("merged_by") or {}).get("login")
        merge_sha = pr.get("merge_commit_sha")
        if merged_by != OWNER:
            return {"status": "STOP", "reason": "merged_by_non_owner",
                    "merged_by": merged_by, **evidence}
        if ci != "SUCCESS":
            return {"status": "STOP", "reason": "merged_without_green_exact_head_ci",
                    "merged_by": merged_by, **evidence}
        if not merge_on_default(gh, task, merge_sha):
            return {"status": "STOP", "reason": "merge_commit_not_on_default_branch",
                    "merge_sha": merge_sha, **evidence}
        return {"status": "INTEGRATED", "reason": "owner_merged_verified_head",
                "merged_by": merged_by, "merge_sha": merge_sha, **evidence}
    if pr.get("state") != "open":
        return {"status": "STOP", "reason": "pr_state_unverified", "state": pr.get("state")}
    if ci == "FAILURE":
        return {"status": "REJECTED", "reason": "required_ci_failed", **evidence}
    if ci != "SUCCESS":
        return {"status": "PENDING_CI", "reason": "required_ci_pending", **evidence}
    return {"status": ELIGIBLE, "reason": "ready_for_owner_review_and_merge", **evidence}
