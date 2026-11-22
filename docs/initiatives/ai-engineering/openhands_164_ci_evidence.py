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


def _aggregate_from_runs(runs: list[dict[str, Any]]) -> str:
    if not runs:
        return "PENDING"
    for run in runs:
        conclusion = run.get("conclusion")
        status = run.get("status")
        if status in PENDINGISH or conclusion in PENDINGISH:
            return "PENDING"
        if conclusion in NON_PASS:
            return "FAILURE"
        if conclusion not in ("success", "skipped"):
            return "UNKNOWN"
    return "SUCCESS"


def _security_from_runs(runs: list[dict[str, Any]]) -> str:
    security = [r for r in runs if "gitleaks" in (r.get("name") or "").lower()
                or "security" in (r.get("name") or "").lower()]
    if not security:
        return "PENDING"
    for run in security:
        conclusion = run.get("conclusion")
        status = run.get("status")
        if status in PENDINGISH or conclusion in PENDINGISH:
            return "PENDING"
        if conclusion in NON_PASS:
            return "FAILURE"
        if conclusion not in ("success", "skipped"):
            return "UNKNOWN"
    return "SUCCESS"


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
        runs = transport("GET", f"{api}/commits/{head_sha}/check-runs?per_page=100", token)
        items = runs.get("check_runs") if isinstance(runs, dict) else None
        if not isinstance(items, list) or len(items) >= 100:
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
    ev2, _ = exact_head_ci_from_check_runs(9, transport=ok_transport, token="x")
    assert ev2 is not None and ev2.verified()
    assert pr_number_from_url("https://github.com/DaniilSydorenko/haversine-geolocation/pull/42") == 42
    print("PASS: #164 exact-head CI evidence mapping")


if __name__ == "__main__":
    self_test()