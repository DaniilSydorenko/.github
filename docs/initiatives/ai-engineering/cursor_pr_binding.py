"""Discover and independently verify the PR produced by one managed Cursor run.

The provider's git.branches[] (repoUrl/branch/prUrl) is a CANDIDATE only. The
PR is bound to the lease only after GitHub confirms repository, base, head
branch, non-fork origin, ancestry from the exact starting SHA, a bounded file
list within the task scope, and no competing open PR.
"""
from __future__ import annotations

import re
from typing import Any

from cursor_bundle_builder import open_pull_requests
from cursor_tasks import CursorTask

SHA = re.compile(r"[0-9a-f]{40}\Z")
PR_URL = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/pull/([1-9][0-9]*)\Z")


def _stop(reason: str, **detail: Any) -> dict[str, Any]:
    return {"decision": "STOP", "reason": reason, **detail}


def pr_files(gh: Any, repository: str, number: int, *, max_pages: int = 3) -> list[str] | None:
    names: list[str] = []
    for page in range(1, max_pages + 1):
        batch = gh.get_json(f"/repos/{repository}/pulls/{number}/files",
                            {"per_page": "100", "page": str(page)})
        if not isinstance(batch, list):
            return None
        for item in batch:
            if not isinstance(item, dict) or not isinstance(item.get("filename"), str):
                return None
            names.append(item["filename"])
            if isinstance(item.get("previous_filename"), str):
                names.append(item["previous_filename"])  # renames touch both paths
        if len(batch) < 100:
            return names
    return None


def candidates_from_provider(task: CursorTask, branches: list[dict[str, Any]]) -> dict[str, Any]:
    want = "github.com/" + task.repository
    mine = [b for b in branches if b.get("repoUrl") == want]
    foreign = [b for b in branches if b.get("repoUrl") != want]
    if foreign:
        return _stop("provider_reported_foreign_repository",
                     repos=sorted({str(b.get("repoUrl")) for b in foreign}))
    urls = sorted({b["prUrl"] for b in mine if isinstance(b.get("prUrl"), str)})
    names = sorted({b["branch"] for b in mine if isinstance(b.get("branch"), str)})
    return {"pr_urls": urls, "branches": names}


def discover_and_verify(gh: Any, task: CursorTask, *, provider_branches: list[dict[str, Any]],
                        starting_sha: str, allow_merged: bool = False) -> dict[str, Any]:
    """allow_merged is only for re-verifying a PR already bound to the lease."""
    """Return {"decision": "BIND", pr facts} or a STOP/NO_PR/WAIT result."""
    cand = candidates_from_provider(task, provider_branches)
    if cand.get("decision") == "STOP":
        return cand
    numbers: set[int] = set()
    for url in cand["pr_urls"]:
        match = PR_URL.fullmatch(url)
        if not match or match.group(1) != task.repository:
            return _stop("provider_pr_url_not_in_task_repository", url=url)
        numbers.add(int(match.group(2)))
    if not numbers and cand["branches"]:
        owner = task.repository.split("/")[0]
        for branch in cand["branches"]:
            found = gh.get_json(f"/repos/{task.repository}/pulls",
                                {"head": f"{owner}:{branch}", "state": "all", "per_page": "10"})
            if not isinstance(found, list):
                return _stop("branch_pr_lookup_failed", branch=branch)
            numbers.update(p["number"] for p in found if isinstance(p, dict)
                           and type(p.get("number")) is int)
    if not numbers:
        return {"decision": "NO_PR", "reason": "provider_produced_no_pull_request",
                "branches": cand["branches"]}
    if len(numbers) != 1:
        return _stop("multiple_candidate_prs", prs=sorted(numbers))
    number = numbers.pop()

    pr = gh.get_json(f"/repos/{task.repository}/pulls/{number}")
    if not isinstance(pr, dict):
        return _stop("pr_unreadable", pr=number)
    head, base = pr.get("head") or {}, pr.get("base") or {}
    head_sha = head.get("sha")
    if (base.get("ref") != task.default_branch
            or (base.get("repo") or {}).get("full_name") != task.repository):
        return _stop("pr_wrong_base", pr=number, base=base.get("ref"))
    if (head.get("repo") or {}).get("full_name") != task.repository:
        return _stop("pr_from_fork_or_other_repository", pr=number)
    if not isinstance(head.get("ref"), str) or not head["ref"].startswith("cursor/"):
        return _stop("pr_head_not_a_cursor_branch", pr=number, head_ref=head.get("ref"))
    if cand["branches"] and head["ref"] not in cand["branches"]:
        return _stop("pr_head_branch_not_reported_by_provider", pr=number)
    if not (isinstance(head_sha, str) and SHA.fullmatch(head_sha)):
        return _stop("pr_head_sha_invalid", pr=number)
    if pr.get("merged") is True and not allow_merged:
        return _stop("pr_already_merged_before_acceptance", pr=number)
    if pr.get("state") != "open" and pr.get("merged") is not True:
        return {"decision": "REJECTED", "reason": "pr_closed_without_acceptance", "pr": number}

    compare = gh.get_json(f"/repos/{task.repository}/compare/{starting_sha}...{head_sha}")
    if not (isinstance(compare, dict) and compare.get("status") in ("ahead", "identical")
            and compare.get("behind_by") == 0):
        return _stop("pr_head_not_descended_from_starting_sha", pr=number)

    files = pr_files(gh, task.repository, number)
    if files is None:
        return _stop("pr_file_inventory_incomplete", pr=number)
    outside = sorted(set(files) - set(task.allowed_paths))
    if not files:
        return _stop("pr_changes_no_files", pr=number)
    if outside:
        return _stop("pr_out_of_scope_changes", pr=number, paths=outside)

    others = open_pull_requests(gh, task.repository)
    if others is None:
        return _stop("open_pr_inventory_incomplete")
    competing = sorted(p.get("number") for p in others if p.get("number") != number)
    if competing:
        return _stop("competing_open_prs", prs=competing)
    return {
        "decision": "BIND",
        "pr_number": number,
        "pr_url": f"https://github.com/{task.repository}/pull/{number}",
        "head_sha": head_sha,
        "head_ref": head["ref"],
        "files": sorted(set(files)),
    }
