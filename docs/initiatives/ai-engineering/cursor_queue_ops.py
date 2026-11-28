"""Queue operations used by the protected delivery cycle (#226).

The owner request names a repository, ordered issues and per-issue allowed
paths. Everything else comes from trusted sources: the default branch and the
required checks from GitHub, issue state from GitHub, the model from the
registry. Issue text is never parsed as authority; it is read only to BLOCK.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

import cursor_queue as q
from cursor_tasks import DEFAULT_MODEL, CursorTask

PR_NUMBER = re.compile(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/([1-9][0-9]*)\Z")


def required_checks(gh: Any, repository: str, branch: str) -> list[str]:
    """Required status checks of the default branch from GitHub; none = STOP."""
    contexts: list[str] = []
    rules = gh.get_json(f"/repos/{repository}/rules/branches/{branch}")
    if not isinstance(rules, list):
        raise q.QueueError("target branch rules unreadable")
    for rule in rules:
        if isinstance(rule, dict) and rule.get("type") == "required_status_checks":
            for c in ((rule.get("parameters") or {}).get("required_status_checks") or []):
                if isinstance(c, dict) and isinstance(c.get("context"), str):
                    contexts.append(c["context"])
    contexts = sorted(set(contexts))
    if not contexts:
        raise q.QueueError("target branch has no verifiable required checks")
    return contexts


def _referencing_open_prs(open_prs: list[Any], issue: int) -> list[int]:
    pattern = re.compile(rf"(?<![0-9A-Za-z/])#{issue}(?![0-9])")
    return sorted(p["number"] for p in open_prs if isinstance(p, dict)
                  and type(p.get("number")) is int
                  and pattern.search(f"{p.get('title') or ''}\n{p.get('body') or ''}"))


def build_spec(gh: Any, request: Any) -> dict[str, Any]:
    """Owner request -> full queue spec, or QueueError (nothing written)."""
    if not isinstance(request, dict) or not set(request) <= {
            "queue_id", "repository", "issues", "allowed_paths", "dependencies",
            "accept_subagent_risk", "max_launches"}:
        raise q.QueueError("queue request shape invalid")
    repository = request.get("repository")
    if repository not in q.ALLOWED_REPOSITORIES:
        raise q.QueueError("repository not allowlisted")
    if repository in q.PRIVATE_REPOSITORIES:
        # Checked before any read, so nothing about the target reaches public logs.
        raise q.QueueError("private repository needs a private control plane")
    issues = request.get("issues")
    if (not isinstance(issues, list) or not issues
            or any(type(n) is not int or n <= 0 for n in issues)):
        raise q.QueueError("issues must be a non-empty list of positive integers")
    paths = request.get("allowed_paths")
    deps = request.get("dependencies", {})
    if (not isinstance(paths, dict) or set(paths) != {str(n) for n in issues}
            or not isinstance(deps, dict) or not set(deps) <= {str(n) for n in issues}):
        raise q.QueueError("allowed_paths must name exactly the queued issues")
    repo = gh.get_json(f"/repos/{repository}")
    if not isinstance(repo, dict) or repo.get("private") is not False:
        raise q.QueueError("target repository is not verifiably public")
    branch = repo.get("default_branch")
    if not isinstance(branch, str) or not branch:
        raise q.QueueError("target default branch unreadable")
    checks = required_checks(gh, repository, branch)
    open_prs = gh.get_json(f"/repos/{repository}/pulls", {"state": "open", "per_page": "100"})
    if not isinstance(open_prs, list) or len(open_prs) >= 100:
        raise q.QueueError("open pull request inventory incomplete")
    for n in issues:
        issue = gh.get_json(f"/repos/{repository}/issues/{n}")
        if not isinstance(issue, dict) or "pull_request" in issue:
            raise q.QueueError(f"#{n} is not an issue")
        if issue.get("state") != "open":
            raise q.QueueError(f"#{n} is not open")
        competing = _referencing_open_prs(open_prs, n)
        if competing:
            # Phase 1 blocks; verified existing-PR continuation is a later phase.
            raise q.QueueError(f"#{n} has open PR(s) {competing}; resolve before queueing")
    spec = {
        "schema": q.SCHEMA, "queue_id": request.get("queue_id"), "repository": repository,
        "default_branch": branch, "model": DEFAULT_MODEL,
        "accept_subagent_risk": request.get("accept_subagent_risk", False),
        "max_launches": request.get("max_launches", len(issues)),
        "tasks": [{"issue": n, "order": i + 1, "allowed_paths": paths[str(n)],
                   "required_checks": checks, "dependencies": deps.get(str(n), [])}
                  for i, n in enumerate(issues)],
    }
    q.validate_spec(spec)
    return spec


def dispatch_gate(doc: Mapping[str, Any], task: CursorTask) -> str | None:
    """Why a NEW dispatch for ``task`` must not start now, or None."""
    head = q.next_task(doc)
    if head is None:
        return "queue_complete"
    if (head.repository, head.issue) != (task.repository, task.issue):
        return "task_is_not_queue_head"
    state = doc["progress"][str(head.issue)]["state"]
    if state != "PENDING":
        return "queue_head_" + state.lower()
    launched = sum(p["state"] != "PENDING" for p in doc["progress"].values())
    if launched >= doc["spec"]["max_launches"]:
        return "queue_launch_limit_reached"
    if any(doc["progress"][str(d)]["state"] != "DONE" for d in head.dependencies):
        return "queue_dependency_not_done"
    return None


def previous_pr(doc: Mapping[str, Any]) -> int | None:
    """PR of the most recent DONE task (App-written evidence), for the handoff."""
    last = None
    for t in doc["spec"]["tasks"]:
        p = doc["progress"][str(t["issue"])]
        if p["state"] == "DONE":
            last = p["evidence"].get("pr_number")
    return last if type(last) is int else None


def binding(doc: Mapping[str, Any], task: CursorTask) -> dict[str, Any]:
    return {"spec_digest": doc["spec_digest"], "repository": task.repository,
            "issue": task.issue, "accept_subagent_risk": doc["spec"]["accept_subagent_risk"]}


def sync_progress(store: Any, doc: Mapping[str, Any], result: Mapping[str, Any], *,
                  workflow_run_id: str) -> dict[str, Any] | None:
    """Record what this run verifiably did to the queue head; never authority."""
    head = q.next_task(doc)
    if head is None:
        return None
    state = doc["progress"][str(head.issue)]["state"]
    lease = store.read().state
    steps = [s.get("outcome") for s in result.get("lifecycle_steps") or [result]]
    digest = doc["spec_digest"]
    if state == "PENDING" and lease.get("phase") != "IDLE" \
            and lease.get("source_issue_url") == head.issue_url:
        return q.set_progress(store, head.issue, "RUNNING",
                              {"request_id": lease.get("request_id"),
                               "workflow_run_id": workflow_run_id}, expected_spec_digest=digest)
    if state == "RUNNING" and "RELEASED" in steps:
        match = PR_NUMBER.fullmatch(str(result.get("pr") or ""))
        acceptance = result.get("acceptance") or {}
        return q.set_progress(store, head.issue, "DONE",
                              {"pr_number": int(match.group(1)) if match else None,
                               "exact_head": acceptance.get("exact_head"),
                               "merge_sha": acceptance.get("merge_sha"),
                               "workflow_run_id": workflow_run_id}, expected_spec_digest=digest)
    if state == "RUNNING" and result.get("step") == "reject" \
            and result.get("outcome") not in ("STOP",) and lease.get("phase") == "IDLE":
        return q.set_progress(store, head.issue, "BLOCKED",
                              {"reason": "owner_rejected", "workflow_run_id": workflow_run_id},
                              expected_spec_digest=digest)
    return None
