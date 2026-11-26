#!/usr/bin/env python3
"""Authenticated exact-head CI/security evidence for published #164 Draft PRs."""
from __future__ import annotations

import re
from typing import Any, Callable

from openhands_164_vertical_integration import CiEvidence

SHA = re.compile(r"[0-9a-f]{40}\Z")
TERMINAL_CONCLUSIONS = frozenset({"success", "failure", "cancelled", "timed_out", "action_required", "skipped", "stale"})
NON_PASS = frozenset({"failure", "cancelled", "timed_out", "action_required", "stale"})
PENDINGISH = frozenset({None, "", "pending", "queued", "waiting", "requested", "in_progress"})
PAGE_SIZE = 100
MAX_CHECK_RUN_PAGES = 5


def _classify(runs: list[dict[str, Any]]) -> str:
    """FAILURE beats PENDING beats UNKNOWN beats SUCCESS, independent of run order.

    A red check is final the moment it completes; it must not be hidden behind
    another check that is still running just because that one was listed first.
    """
    if not runs:
        return "PENDING"
    pending = unknown = False
    for run in runs:
        conclusion = run.get("conclusion")
        status = run.get("status")
        if conclusion in NON_PASS:
            return "FAILURE"
        if status in PENDINGISH or conclusion in PENDINGISH:
            pending = True
        elif conclusion not in ("success", "skipped"):
            unknown = True
    if pending:
        return "PENDING"
    if unknown:
        return "UNKNOWN"
    return "SUCCESS"


def _aggregate_from_runs(runs: list[dict[str, Any]]) -> str:
    return _classify(runs)


def _security_from_runs(runs: list[dict[str, Any]]) -> str:
    security = [r for r in runs if "gitleaks" in (r.get("name") or "").lower()
                or "security" in (r.get("name") or "").lower()]
    if not security:
        return "PENDING"
    return _classify(security)


def exact_head_ci_from_check_runs(
    pr_number: int,
  *,
    transport: Callable[[str, str, str], Any],
    token: str,
    repo: str = "DaniilSydorenko/haversine-geolocation",
) -> tuple[CiEvidence | None, dict[str, Any] | None]:
    api = f"https://api.github.com/repos/{repo}"
    try:
        pr = transport("GET", f"{api}/pulls/{pr_number}", token)
        head_sha = pr.get("head", {}).get("sha") if isinstance(pr, dict) else None
        if not isinstance(head_sha, str) or not SHA.fullmatch(head_sha):
            return None, {"decision": "STOP", "reason": "published_pr_head_unverified"}
        items: list[Any] = []
        for page in range(1, MAX_CHECK_RUN_PAGES + 1):
            runs = transport("GET", f"{api}/commits/{head_sha}/check-runs?per_page={PAGE_SIZE}&page={page}", token)
            batch = runs.get("check_runs") if isinstance(runs, dict) else None
            if not isinstance(batch, list):
                return None, {"decision": "STOP", "reason": "check_run_inventory_incomplete"}
            items.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
        else:
            # Every page was full up to the cap: the inventory may still be incomplete.
            return None, {"decision": "STOP", "reason": "check_run_inventory_incomplete"}
        clean = []
        for run in items:
            if not isinstance(run, dict):
                return None, {"decision": "STOP", "reason": "invalid_check_run"}
            conclusion = run.get("conclusion")
            if conclusion is not None and conclusion not in TERMINAL_CONCLUSIONS:
                return None, {"decision": "STOP", "reason": "unknown_check_conclusion"}
            clean.append(run)
        return CiEvidence(_aggregate_from_runs(clean), _security_from_runs(clean)), None
    except Exception as exc:
        return None, {"decision": "STOP", "reason": "exact_head_ci_unavailable", "detail": type(exc).__name__}


def pr_number_from_url(pr_url: str) -> int | None:
    match = re.search(r"/pull/([1-9][0-9]*)\Z", pr_url)
    return int(match.group(1)) if match else None


def self_test() -> None:
    pr = {"head": {"sha": "a" * 40}}
    pending_runs = {"check_runs": [{"name": "CI", "status": "queued", "conclusion": None},
                                   {"name": "Gitleaks", "status": "in_progress", "conclusion": None}]}
    ok_runs = {"check_runs": [{"name": "CI", "status": "completed", "conclusion": "success"},
                              {"name": "Gitleaks", "status": "completed", "conclusion": "success"}]}

    def pending_transport(method, url, token):
        if "/pulls/9" in url:
            return pr
        return pending_runs

    def ok_transport(method, url, token):
        if "/pulls/9" in url:
            return pr
        return ok_runs

    ev, err = exact_head_ci_from_check_runs(9, transport=pending_transport, token="x")
    assert err is None and ev is not None and ev.aggregate == "PENDING"
    mixed = [{"name": "CI", "status": "in_progress", "conclusion": None},
             {"name": "Lint", "status": "completed", "conclusion": "failure"}]
    assert _aggregate_from_runs(mixed) == "FAILURE" == _aggregate_from_runs(mixed[::-1])
    ev2, _ = exact_head_ci_from_check_runs(9, transport=ok_transport, token="x")
    assert ev2 is not None and ev2.verified()
    assert pr_number_from_url("https://github.com/DaniilSydorenko/haversine-geolocation/pull/42") == 42
    print("PASS: #164 exact-head CI evidence mapping")


if __name__ == "__main__":
    self_test()