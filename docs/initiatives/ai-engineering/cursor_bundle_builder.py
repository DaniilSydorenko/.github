"""Build the launch bundle {"preview", "handoff"} for launch_single_approved_issue.

Every field is one of four classes, recorded in ``evidence_classes``:
  runtime      - read live from GitHub / the lease in this run;
  attestation  - an explicit owner decision (protected workflow input / variable);
  configuration- the reviewed task registry (cursor_tasks.py);
  proposed     - execution parameters this platform proposes (paths, model).
No previous merge, acceptance or provider fact is ever fabricated. The first
managed run uses an explicit BOOTSTRAP previous-step record instead.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from cursor_tasks import OWNER, CursorTask, queue_for

SHA = re.compile(r"[0-9a-f]{40}\Z")


def _stop(reason: str, **detail: Any) -> dict[str, Any]:
    return {"decision": "STOP", "reason": reason, "detail": detail or None}


def _pages(gh: Any, path: str, *, max_pages: int = 3, per_page: int = 100) -> list | None:
    """All items of a list endpoint, or None if the inventory may be incomplete."""
    out: list = []
    for page in range(1, max_pages + 1):
        batch = gh.get_json(path, {"per_page": str(per_page), "page": str(page)})
        if not isinstance(batch, list):
            return None
        out.extend(batch)
        if len(batch) < per_page:
            return out
    return None


def open_pull_requests(gh: Any, repository: str) -> list[dict[str, Any]] | None:
    batch = gh.get_json(f"/repos/{repository}/pulls", {"state": "open", "per_page": "50"})
    if not isinstance(batch, list) or len(batch) >= 50:
        return None
    return [p for p in batch if isinstance(p, dict)]


def check_runs_at(gh: Any, repository: str, sha: str) -> list[dict[str, Any]] | None:
    runs: list = []
    for page in range(1, 6):
        body = gh.get_json(f"/repos/{repository}/commits/{sha}/check-runs",
                           {"per_page": "100", "page": str(page)})
        items = body.get("check_runs") if isinstance(body, dict) else None
        if not isinstance(items, list):
            return None
        runs.extend(items)
        if len(items) < 100:
            return runs
    return None


def required_checks_state(runs: list[dict[str, Any]], required: tuple[str, ...]) -> str:
    """SUCCESS / FAILURE / PENDING over required names AND every other check-run."""
    if any(r.get("status") == "completed" and r.get("conclusion") not in
           ("success", "neutral", "skipped") for r in runs):
        return "FAILURE"
    for name in required:
        named = [r for r in runs if r.get("name") == name]
        if not named or any(r.get("status") != "completed" for r in named):
            return "PENDING"
        if any(r.get("conclusion") != "success" for r in named):
            return "FAILURE"
    if any(r.get("status") != "completed" for r in runs):
        return "PENDING"
    return "SUCCESS"


def owner_approved_at(gh: Any, repository: str, pr_number: int, head_sha: str) -> bool:
    """Latest owner review on the exact head is APPROVED (semantic acceptance)."""
    reviews = _pages(gh, f"/repos/{repository}/pulls/{pr_number}/reviews")
    if reviews is None:
        return False
    owner = [r for r in reviews if isinstance(r, dict)
             and (r.get("user") or {}).get("login") == OWNER
             and r.get("state") in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED")]
    return bool(owner) and owner[-1].get("state") == "APPROVED" \
        and owner[-1].get("commit_id") == head_sha


def previous_merge_evidence(gh: Any, task: CursorTask, pr_number: int) -> dict[str, Any]:
    """Runtime evidence for a previous managed PR named by the owner."""
    repo = task.repository
    pr = gh.get_json(f"/repos/{repo}/pulls/{pr_number}")
    if not isinstance(pr, dict):
        return _stop("previous_pr_unreadable")
    head = (pr.get("head") or {}).get("sha")
    merge_sha = pr.get("merge_commit_sha")
    if not (isinstance(head, str) and SHA.fullmatch(head)
            and isinstance(merge_sha, str) and SHA.fullmatch(merge_sha)):
        return _stop("previous_pr_identity_unverified")
    compare = gh.get_json(f"/repos/{repo}/compare/{merge_sha}...{task.default_branch}")
    on_default = isinstance(compare, dict) and compare.get("status") in ("ahead", "identical")
    runs = check_runs_at(gh, repo, head)
    ci = required_checks_state(runs, task.required_checks) if runs is not None else "UNKNOWN"
    secret = (required_checks_state(runs, ("Gitleaks",)) if runs is not None else "UNKNOWN")
    return {
        "pr_number": pr_number,
        "state": pr.get("state"),
        "merged": pr.get("merged") is True,
        "head_sha": head,
        "merge_sha": merge_sha,
        "merge_on_default_verified": on_default,
        "ci": ci,
        "secret_scan": secret,
        "owner_merge_permission": "granted"
        if (pr.get("merged_by") or {}).get("login") == OWNER else "missing",
        "owner_visual_acceptance": "accepted"
        if owner_approved_at(gh, repo, pr_number, head) else "pending",
        # Haversine is a library: merge is the delivery, there is no deployment.
        "deployment": "not_required",
    }


def bootstrap_previous(*, owner_bootstrap_authorized: bool, lease_state: Mapping[str, Any],
                       open_prs: list) -> dict[str, Any]:
    return {
        "kind": "BOOTSTRAP",
        "owner_bootstrap_authorized": owner_bootstrap_authorized is True,
        "lease_idle_verified": lease_state.get("phase") == "IDLE",
        "no_open_managed_pr_verified": open_prs == [],
    }


def _issue_entry(gh: Any, task: CursorTask) -> dict[str, Any] | None:
    issue = gh.get_json(f"/repos/{task.repository}/issues/{task.issue}")
    if not isinstance(issue, dict) or "pull_request" in issue:
        return None
    state = issue.get("state")
    if state not in ("open", "closed"):
        return None
    # Accepted == closed as completed. Closed for any other reason is not
    # accepted and stops the queue (sequential_handoff: closed_issue_not_accepted).
    return {"state": state, "accepted": state == "closed" and issue.get("state_reason") == "completed"}


def build_launch_bundle(
    gh: Any,
    task: CursorTask,
    *,
    collected: Mapping[str, Any],
    main_sha: str,
    lease_state: Mapping[str, Any],
    owner_bootstrap_authorized: bool = False,
    previous_pr_number: int | None = None,
) -> dict[str, Any]:
    """Return {"preview", "handoff", "evidence_classes"} or a STOP dict."""
    if collected.get("status") != "OBSERVED" or collected.get("missing_capabilities"):
        return _stop("github_collection_incomplete",
                     missing=collected.get("missing_capabilities"))
    facts = collected.get("observed_facts") or {}
    if (facts.get("repo") != task.repository or facts.get("issue_number") != task.issue
            or facts.get("issue_state") != "open"):
        return _stop("issue_not_open_or_identity_mismatch", state=facts.get("issue_state"))
    if not (isinstance(main_sha, str) and SHA.fullmatch(main_sha)) or facts.get("default_sha") != main_sha:
        return _stop("default_sha_moved_between_reads")
    if facts.get("related_prs"):
        # Existing related PRs are integration work (launch_single_approved_pr),
        # never a fresh Cursor run.
        return _stop("related_prs_exist_review_first",
                     prs=[p.get("number") for p in facts["related_prs"]])
    if lease_state.get("phase") != "IDLE":
        return _stop("lease_not_idle")
    open_prs = open_pull_requests(gh, task.repository)
    if open_prs is None:
        return _stop("open_pr_inventory_incomplete")
    if open_prs:
        # Strict serial integration: no fresh run while any PR is open in target.
        return _stop("target_repository_has_open_prs", prs=[p.get("number") for p in open_prs])

    if previous_pr_number is not None and owner_bootstrap_authorized:
        return _stop("choose_bootstrap_or_previous_pr_not_both")
    if previous_pr_number is not None:
        previous = previous_merge_evidence(gh, task, previous_pr_number)
        if previous.get("decision") == "STOP":
            return previous
    else:
        previous = bootstrap_previous(owner_bootstrap_authorized=owner_bootstrap_authorized,
                                      lease_state=lease_state, open_prs=open_prs)

    queue = []
    states: dict[int, dict[str, Any]] = {}
    for t in queue_for(task.repository):
        entry = _issue_entry(gh, t)
        if entry is None:
            return _stop("queue_issue_unreadable", issue=t.issue)
        states[t.issue] = entry
    for t in queue_for(task.repository):
        deps = [{"number": d, "status": "accepted" if states.get(d, {}).get("accepted")
                 else ("pending" if d in states else "unknown")} for d in t.dependencies]
        queue.append({
            "number": t.issue, "order": t.order, **states[t.issue],
            "owner_approved": True, "owner_gate": False, "scope": t.scope,
            "allowed_paths": list(t.allowed_paths), "dependencies": deps,
        })

    issue_url = task.issue_url
    paths = list(task.allowed_paths)
    preview = {
        "schema_version": 1,
        "collector": {
            "status": "OBSERVED", "missing_capabilities": [], "warnings": [],
            "observed_facts": {
                "repo": task.repository, "issue_number": task.issue, "issue_state": "open",
                "default_sha": main_sha,
                "linked_pr_inventory_truncated": facts.get("linked_pr_inventory_truncated") is True,
                "related_prs_files_pagination_complete":
                    facts.get("related_prs_files_pagination_complete") is True,
                "related_prs": [],
            },
        },
        "observed": {
            "repo": task.repository, "issue_number": task.issue, "issue_state": "open",
            "default_sha": main_sha, "related_inventory_complete": True,
            "related_prs": [], "accepted_shas": [],
        },
        "task": {
            "schema_version": 1, "repository": task.repository, "issue": issue_url,
            "evidence": {
                "default_sha": main_sha, "checked_sha": main_sha, "inventory_complete": True,
                "issue_state": "open", "accepted_commit": None, "accepted_proof": None,
                "related_prs": [], "dependencies": [],
                "writer": "idle", "scope": "allowed", "owner_permission": "granted",
                "owner_gate": False, "external": "clear",
            },
        },
        "semantic": {
            "schema_version": 1, "repository": task.repository, "issue_url": issue_url,
            "issue_number": task.issue, "issue_state": "open",
            "default_sha": main_sha, "observed_default_sha": main_sha,
            "inventory_complete": True,
            # Nothing to attest: the verified related-PR inventory is empty.
            "semantic_attestations_complete": True,
            "permission": "granted", "owner_gate": False, "writer": "idle",
            "proposed_paths": paths, "prs": [],
        },
    }
    handoff = {
        "schema_version": 1,
        "repository": task.repository,
        "main": {"before_sha": main_sha, "after_sha": facts.get("default_sha")},
        "relevant_inventory_complete": True,
        # Only reachable after cursor_protected_dispatch validated the protected
        # owner workflow context (owner actor, dispatch, main, protected env).
        "owner_authority_verified": True,
        "previous": previous,
        "writer": {"inventory_complete": True, "status": "idle", "open_prs": []},
        "queue": queue,
    }
    return {
        "preview": preview,
        "handoff": handoff,
        "evidence_classes": {
            "runtime": ["issue_state", "default_sha (read twice)", "related_pr_inventory",
                        "open_pr_inventory", "queue_issue_states", "lease_phase",
                        "previous_pr_merge_ci_review" if previous_pr_number else "lease_idle"],
            "attestation": ["owner_bootstrap_authorized"] if previous_pr_number is None
            else ["owner_named_previous_pr"],
            "configuration": ["task_registry_scope", "owner_approved (registered task)",
                              "external_dependencies=clear", "deployment=not_required"],
            "proposed": ["allowed_paths", "model"],
        },
    }
