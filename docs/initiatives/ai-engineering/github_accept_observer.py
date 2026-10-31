#!/usr/bin/env python3
"""Read-only PR acceptance observer (Hello World V3).

Observes GitHub REST facts for one owner-chosen pull request. Never dispatches
Cursor, never grants git write, and never treats Issue text, webhook payloads,
or comment strings as owner authorization.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from trusted_github_evidence import (
    GitHubHTTPError,
    SHA,
    _fetch_pull,
    _parse_repo,
    _recent_default_commits,
    client_from_environment,
)

GATE_STATUSES = frozenset(("WAIT_PR", "WAIT_CI", "NEEDS_EVIDENCE", "OWNER_GATE", "STOP"))

CHECK_SUCCESS = frozenset(("success",))
CHECK_PENDING = frozenset(("queued", "in_progress", "pending", "waiting", "requested"))
CHECK_FAILED = frozenset(("failure", "cancelled", "timed_out", "action_required", "stale", "skipped"))


def _envelope(
    status: str,
    reason: str,
    *,
    observed: Dict[str, Any],
    missing: Optional[List[str]] = None,
    warnings: Optional[List[str]] = None,
    owner_domain_acceptance: str = "UNKNOWN",
    global_writer_authorization: str = "UNKNOWN",
    untrusted_hints_recorded: bool = False,
) -> dict:
    assert status in GATE_STATUSES
    if owner_domain_acceptance not in ("UNKNOWN", "OWNER_GATE"):
        owner_domain_acceptance = "UNKNOWN"
    if global_writer_authorization not in ("UNKNOWN", "OWNER_GATE"):
        global_writer_authorization = "UNKNOWN"
    return {
        "status": status,
        "reason": reason,
        "cursor_launched": False,
        "git_write": False,
        "owner_domain_acceptance": owner_domain_acceptance,
        "global_writer_authorization": global_writer_authorization,
        "untrusted_acceptance_hints_recorded": untrusted_hints_recorded,
        "missing_capabilities": list(missing or []),
        "warnings": list(warnings or []),
        "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "observed_facts": observed,
    }


def _record_untrusted_hints(hints: Optional[Mapping[str, Any]]) -> Tuple[bool, List[str]]:
    """Sanitize caller-supplied untrusted acceptance hints; never act on them."""
    warnings: List[str] = []
    if not hints:
        return False, warnings
    warnings.append("Untrusted acceptance hints supplied and ignored")
    if hints.get("approved") is True or hints.get("owner_approved") is True:
        warnings.append("Ignored forged boolean approval in untrusted snapshot")
    if hints.get("webhook_action") in ("closed", "merged", "ready_for_review"):
        warnings.append("Ignored webhook-style action in untrusted snapshot")
    if isinstance(hints.get("issue_comment"), str) and hints["issue_comment"].strip():
        warnings.append("Ignored issue/PR comment text as owner attestation")
    return True, warnings


def _fetch_check_runs(
    transport: Any,
    owner: str,
    name: str,
    head_sha: str,
    *,
    per_page: int = 100,
    max_pages: int = 3,
) -> Tuple[List[dict], bool]:
    collected: List[dict] = []
    path = f"/repos/{owner}/{name}/commits/{head_sha}/check-runs"
    for page in range(1, max_pages + 1):
        batch = transport.get_json(path, {"per_page": str(per_page), "page": str(page)})
        if not isinstance(batch, dict):
            raise GitHubHTTPError(502, path, "check-runs response is not an object")
        runs = batch.get("check_runs")
        if not isinstance(runs, list):
            raise GitHubHTTPError(502, path, "check_runs missing")
        for item in runs:
            if isinstance(item, dict):
                collected.append(item)
        if len(runs) < per_page:
            return collected, True
    return collected, False


def _summarize_exact_head_checks(
    runs: Sequence[dict],
    head_sha: str,
    *,
    pagination_complete: bool,
) -> dict:
    exact: List[dict] = []
    non_head_success = 0
    for run in runs:
        if not isinstance(run, dict):
            continue
        run_head = run.get("head_sha")
        name = run.get("name") if isinstance(run.get("name"), str) else None
        status = run.get("status")
        conclusion = run.get("conclusion")
        if run_head != head_sha:
            if conclusion in CHECK_SUCCESS:
                non_head_success += 1
            continue
        bucket = "UNKNOWN"
        if status in CHECK_PENDING or conclusion in CHECK_PENDING:
            bucket = "PENDING"
        elif conclusion in CHECK_SUCCESS and status == "completed":
            bucket = "SUCCESS"
        elif conclusion in CHECK_FAILED or (status == "completed" and conclusion not in CHECK_SUCCESS):
            bucket = "FAILED"
        elif status == "completed" and conclusion is None:
            bucket = "UNKNOWN"
        exact.append(
            {
                "name": name,
                "status": status,
                "conclusion": conclusion,
                "head_sha": run_head,
                "classification": bucket,
            }
        )
    classifications = [c["classification"] for c in exact]
    aggregate = "MISSING"
    if not pagination_complete:
        aggregate = "UNKNOWN"
    elif exact:
        if any(x == "FAILED" for x in classifications):
            aggregate = "FAILED"
        elif any(x == "PENDING" for x in classifications):
            aggregate = "PENDING"
        elif any(x == "UNKNOWN" for x in classifications):
            aggregate = "UNKNOWN"
        elif all(x == "SUCCESS" for x in classifications):
            aggregate = "SUCCESS"
    return {
        "exact_head_runs": exact,
        "exact_head_aggregate": aggregate,
        "non_head_success_count": non_head_success,
        "check_runs_pagination_complete": pagination_complete,
    }


def _pull_facts(pull: dict) -> dict:
    head = pull.get("head") if isinstance(pull.get("head"), dict) else {}
    base = pull.get("base") if isinstance(pull.get("base"), dict) else {}
    head_sha = head.get("sha")
    base_sha = base.get("sha")
    draft = bool(pull.get("draft"))
    merged_at = pull.get("merged_at")
    return {
        "number": pull.get("number"),
        "state": pull.get("state"),
        "draft": draft,
        "merged": bool(merged_at),
        "merged_at": merged_at,
        "merge_commit_sha": pull.get("merge_commit_sha"),
        "head_ref": head.get("ref"),
        "head_sha": head_sha if isinstance(head_sha, str) else None,
        "head_sha_observed": isinstance(head_sha, str) and SHA.fullmatch(head_sha) is not None,
        "base_ref": base.get("ref"),
        "base_sha": base_sha if isinstance(base_sha, str) else None,
        "base_sha_observed": isinstance(base_sha, str) and SHA.fullmatch(base_sha) is not None,
    }


def observe_pr_acceptance(
    repository: str,
    pr_number: int,
    *,
    transport: Optional[Any] = None,
    expected_head_sha: Optional[str] = None,
    untrusted_acceptance_hints: Optional[Mapping[str, Any]] = None,
    max_check_pages: int = 3,
    commit_sample: int = 15,
) -> dict:
    """Observe bounded read-only PR acceptance facts for one explicit PR."""
    missing: List[str] = []
    warnings: List[str] = []
    hints_recorded, hint_warnings = _record_untrusted_hints(untrusted_acceptance_hints)
    warnings.extend(hint_warnings)

    observed: Dict[str, Any] = {
        "repository": repository,
        "pr_number": pr_number,
        "expected_head_sha": expected_head_sha,
    }

    if expected_head_sha is not None and (
        not isinstance(expected_head_sha, str) or SHA.fullmatch(expected_head_sha) is None
    ):
        return _envelope(
            "STOP",
            "invalid_expected_head_sha",
            observed=observed,
            warnings=warnings,
            untrusted_hints_recorded=hints_recorded,
        )

    if transport is None:
        transport, cap = client_from_environment()
        if transport is None:
            return _envelope(
                "NEEDS_EVIDENCE",
                "no_authenticated_github_read",
                observed=observed,
                missing=[cap or "authenticated_github_read"],
                warnings=warnings + ["No live GitHub read performed"],
                untrusted_hints_recorded=hints_recorded,
            )

    try:
        owner, name = _parse_repo(repository)
    except ValueError:
        return _envelope(
            "NEEDS_EVIDENCE",
            "invalid_repository_slug",
            observed=observed,
            warnings=warnings,
            untrusted_hints_recorded=hints_recorded,
        )

    try:
        repo_meta = transport.get_json(f"/repos/{owner}/{name}")
        if not isinstance(repo_meta, dict):
            raise GitHubHTTPError(502, f"/repos/{owner}/{name}", "invalid repo metadata")
        default_branch = repo_meta.get("default_branch")
        if not isinstance(default_branch, str) or not default_branch:
            missing.append("default_branch_name")
            default_branch = None
        observed["default_branch"] = default_branch

        pull_a = _fetch_pull(transport, owner, name, pr_number)
        pull_b = _fetch_pull(transport, owner, name, pr_number)
        if pull_a.get("number") != pr_number or pull_b.get("number") != pr_number:
            missing.append("consistent_pr_identity")
            warnings.append("PR number mismatch between request and response")

        facts_a = _pull_facts(pull_a)
        facts_b = _pull_facts(pull_b)
        observed["pr"] = facts_b

        if facts_a["head_sha"] != facts_b["head_sha"]:
            missing.append("stable_pr_head_sha")
            warnings.append("PR HEAD changed during observation")
            observed["pr_head_sha_at_start"] = facts_a["head_sha"]
        if facts_a["base_sha"] != facts_b["base_sha"]:
            missing.append("stable_pr_base_sha")
            warnings.append("PR BASE changed during observation")
        if facts_a["state"] != facts_b["state"] or facts_a["merged"] != facts_b["merged"]:
            missing.append("stable_pr_state")
            warnings.append("PR state changed during observation")

        if not facts_b["head_sha_observed"]:
            missing.append("verifiable_pr_head_sha")
        if not facts_b["base_sha_observed"]:
            missing.append("verifiable_pr_base_sha")

        if expected_head_sha and facts_b["head_sha"] != expected_head_sha:
            return _envelope(
                "STOP",
                "expected_head_sha_stale_or_wrong",
                observed=observed,
                missing=missing,
                warnings=warnings,
                untrusted_hints_recorded=hints_recorded,
            )

        default_sha = None
        if default_branch:
            ref = transport.get_json(f"/repos/{owner}/{name}/git/ref/heads/{default_branch}")
            if isinstance(ref, dict) and isinstance(ref.get("object"), dict):
                sha = ref["object"].get("sha")
                if isinstance(sha, str) and SHA.fullmatch(sha):
                    default_sha = sha
            if default_sha is None:
                missing.append("default_branch_sha")
        observed["default_branch_sha"] = default_sha

        merge_sha = facts_b["merge_commit_sha"]
        merge_reachable = None
        recent_shas: List[str] = []
        if default_branch:
            recent_shas = _recent_default_commits(
                transport, owner, name, default_branch, limit=commit_sample
            )
        observed["default_branch_recent_commit_shas"] = recent_shas
        if facts_b["merged"] and isinstance(merge_sha, str) and SHA.fullmatch(merge_sha):
            merge_reachable = merge_sha in recent_shas
            observed["merge_commit_sha"] = merge_sha
            observed["merge_reachable_from_default_bounded"] = merge_reachable
            if merge_reachable is False:
                missing.append("merge_commit_in_bounded_default_sample")
                warnings.append("Merge commit not in bounded default-branch sample")

        ref_final = None
        if default_branch:
            ref_final = transport.get_json(f"/repos/{owner}/{name}/git/ref/heads/{default_branch}")
        final_default_sha = None
        if isinstance(ref_final, dict) and isinstance(ref_final.get("object"), dict):
            candidate = ref_final["object"].get("sha")
            if isinstance(candidate, str) and SHA.fullmatch(candidate):
                final_default_sha = candidate
        if default_sha and final_default_sha and default_sha != final_default_sha:
            missing.append("stable_default_branch_sha")
            warnings.append("Default branch SHA changed during observation")
            observed["default_branch_sha_at_start"] = default_sha
            observed["default_branch_sha"] = final_default_sha

        head_sha = facts_b["head_sha"]
        check_summary = {
            "exact_head_runs": [],
            "exact_head_aggregate": "MISSING",
            "non_head_success_count": 0,
            "check_runs_pagination_complete": True,
        }
        if head_sha and facts_b["head_sha_observed"]:
            try:
                runs, checks_complete = _fetch_check_runs(
                    transport, owner, name, head_sha, max_pages=max_check_pages
                )
                check_summary = _summarize_exact_head_checks(
                    runs, head_sha, pagination_complete=checks_complete
                )
                if not checks_complete:
                    missing.append("complete_check_runs_pagination")
                    warnings.append("Check-run pagination truncated (bounded max pages)")
            except GitHubHTTPError as exc:
                if exc.status in (403, 429):
                    missing.append("github_checks_read_permission_or_rate_limit")
                else:
                    missing.append(f"github_checks_read_http_{exc.status}")
                check_summary["exact_head_aggregate"] = "UNKNOWN"
                warnings.append("Could not read exact-head check runs")
        else:
            missing.append("head_sha_for_checks")
        observed["checks"] = check_summary

        agg = check_summary["exact_head_aggregate"]
        non_head_ok = check_summary["non_head_success_count"]

        if missing:
            return _envelope(
                "NEEDS_EVIDENCE",
                "incomplete_or_unstable_pr_evidence",
                observed=observed,
                missing=missing,
                warnings=warnings,
                untrusted_hints_recorded=hints_recorded,
            )

        if facts_b["draft"]:
            return _envelope(
                "WAIT_PR",
                "draft_pull_request_not_acceptance_ready",
                observed=observed,
                warnings=warnings,
                untrusted_hints_recorded=hints_recorded,
            )

        if facts_b["state"] == "open" and not facts_b["merged"]:
            if agg in ("MISSING", "UNKNOWN"):
                return _envelope(
                    "WAIT_CI",
                    "open_pr_exact_head_checks_not_proven",
                    observed=observed,
                    warnings=warnings,
                    untrusted_hints_recorded=hints_recorded,
                )
            if agg == "PENDING":
                return _envelope(
                    "WAIT_CI",
                    "required_exact_head_checks_pending",
                    observed=observed,
                    warnings=warnings,
                    untrusted_hints_recorded=hints_recorded,
                )
            if agg == "FAILED":
                return _envelope(
                    "STOP",
                    "exact_head_checks_failed",
                    observed=observed,
                    warnings=warnings,
                    untrusted_hints_recorded=hints_recorded,
                )
            if non_head_ok and agg != "SUCCESS":
                return _envelope(
                    "WAIT_CI",
                    "non_head_check_success_does_not_count",
                    observed=observed,
                    warnings=warnings,
                    untrusted_hints_recorded=hints_recorded,
                )
            return _envelope(
                "OWNER_GATE",
                "open_pr_facts_observed_owner_acceptance_required",
                observed=observed,
                warnings=warnings,
                owner_domain_acceptance="OWNER_GATE",
                global_writer_authorization="UNKNOWN",
                untrusted_hints_recorded=hints_recorded,
            )

        if facts_b["merged"]:
            if agg in ("MISSING", "UNKNOWN", "PENDING"):
                if agg == "MISSING":
                    return _envelope(
                        "STOP",
                        "merged_pr_without_exact_head_checks",
                        observed=observed,
                        warnings=warnings,
                        untrusted_hints_recorded=hints_recorded,
                    )
                return _envelope(
                    "WAIT_CI" if agg == "PENDING" else "NEEDS_EVIDENCE",
                    "merged_pr_checks_incomplete_or_unverified",
                    observed=observed,
                    warnings=warnings,
                    untrusted_hints_recorded=hints_recorded,
                )
            if agg == "FAILED":
                return _envelope(
                    "STOP",
                    "merged_pr_exact_head_checks_failed",
                    observed=observed,
                    warnings=warnings,
                    untrusted_hints_recorded=hints_recorded,
                )
            if non_head_ok and not check_summary["exact_head_runs"]:
                return _envelope(
                    "WAIT_CI",
                    "only_non_head_checks_succeeded",
                    observed=observed,
                    warnings=warnings,
                    untrusted_hints_recorded=hints_recorded,
                )
            return _envelope(
                "OWNER_GATE",
                "merged_and_checks_green_owner_gate_still_required",
                observed=observed,
                warnings=warnings,
                owner_domain_acceptance="OWNER_GATE",
                global_writer_authorization="OWNER_GATE",
                untrusted_hints_recorded=hints_recorded,
            )

        return _envelope(
            "STOP",
            "pr_state_not_open_or_merged",
            observed=observed,
            warnings=warnings,
            untrusted_hints_recorded=hints_recorded,
        )

    except GitHubHTTPError as exc:
        cap = f"github_api_read_http_{exc.status}"
        if exc.status in (403, 429):
            cap = "github_api_rate_limit_or_permission_denied"
        elif exc.status == 404:
            cap = "github_api_not_found_or_repo_pr_mismatch"
        return _envelope(
            "NEEDS_EVIDENCE",
            "github_api_read_failed",
            observed=observed,
            missing=[cap],
            warnings=warnings + [f"GitHub API read failed ({cap})"],
            untrusted_hints_recorded=hints_recorded,
        )


def bounded_live_smoke_draft_pr_147() -> dict:
    """Optional single live read against open Draft PR #147; no acceptance expected."""
    repo = "DaniilSydorenko/.github"
    pr_number = 147
    transport, cap = client_from_environment()
    if transport is None:
        return {"live_read": "UNAVAILABLE", "missing_capabilities": [cap]}
    result = observe_pr_acceptance(repo, pr_number, transport=transport)
    result["live_read"] = "ATTEMPTED"
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(argv or sys.argv[1:])
    if len(argv) == 1 and argv[0] == "--live-smoke-pr-147":
        print(json.dumps(bounded_live_smoke_draft_pr_147(), indent=2, sort_keys=True))
        return 0
    if len(argv) not in (2, 3):
        print(
            "Usage: python3 github_accept_observer.py <owner/repo> <pr-number> [expected-head-sha]\n"
            "       python3 github_accept_observer.py --live-smoke-pr-147",
            file=sys.stderr,
        )
        return 2
    repository, pr_s = argv[0], argv[1]
    expected = argv[2] if len(argv) == 3 else None
    try:
        pr_number = int(pr_s)
    except ValueError:
        print("PR number must be an integer", file=sys.stderr)
        return 2
    result = observe_pr_acceptance(repository, pr_number, expected_head_sha=expected)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
