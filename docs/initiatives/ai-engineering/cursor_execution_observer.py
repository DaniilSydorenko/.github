"""Bounded, GET-only observation of one managed Cursor agent/run.

Never POSTs, never launches a replacement, never retries a create. Uncertain
provider state always keeps the lease. Resumable: each protected workflow run
observes for a bounded number of polls and leaves the lease where it is.
Provider contract: Cursor Cloud Agents API v1 (public beta) GET
/v1/agents/{id} and /v1/agents/{id}/runs/{runId}.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any, Callable

from cursor_readonly import AGENT, RUN, CursorReadError

ACTIVE = frozenset({"CREATING", "RUNNING", "WAITING_FOR_BACKGROUND_WORK"})
TERMINAL = {"FINISHED": "SUCCEEDED", "ERROR": "FAILED",
            "CANCELLED": "CANCELLED", "EXPIRED": "EXPIRED"}
DEFAULT_STALE_AFTER_S = 6 * 3600


def _ts(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()
    except ValueError:
        return None


def _branches(run: dict[str, Any]) -> list[dict[str, Any]]:
    git = run.get("git")
    items = git.get("branches") if isinstance(git, dict) else None
    return [b for b in items if isinstance(b, dict)] if isinstance(items, list) else []


def observe_once(api: Any, agent_id: str, run_id: str, *, now: float,
                 stale_after_s: int = DEFAULT_STALE_AFTER_S) -> dict[str, Any]:
    if not (isinstance(agent_id, str) and AGENT.fullmatch(agent_id)
            and isinstance(run_id, str) and RUN.fullmatch(run_id)):
        return {"state": "UNKNOWN", "reason": "invalid_agent_or_run_identity"}
    try:
        run = api.get_json(f"/v1/agents/{agent_id}/runs/{run_id}")
    except CursorReadError as exc:
        if exc.status == 404:
            return {"state": "AMBIGUOUS", "reason": "run_not_found_for_recorded_identity"}
        return {"state": "UNAVAILABLE", "reason": "provider_read_failed", "status": exc.status}
    if run.get("id") != run_id or run.get("agentId") != agent_id:
        return {"state": "AMBIGUOUS", "reason": "provider_identity_mismatch"}
    status = run.get("status")
    if status in ACTIVE:
        updated = _ts(run.get("updatedAt")) or _ts(run.get("createdAt"))
        if updated is not None and now - updated > stale_after_s:
            return {"state": "STALE", "reason": "active_run_without_progress",
                    "run_status": status, "idle_seconds": int(now - updated)}
        return {"state": "IN_PROGRESS", "reason": "provider_run_active", "run_status": status}
    if status in TERMINAL:
        return {"state": TERMINAL[status], "reason": "provider_run_terminal",
                "run_status": status, "branches": _branches(run)}
    return {"state": "UNKNOWN", "reason": "unsupported_provider_status", "run_status": status}


def observe_run(api: Any, agent_id: str, run_id: str, *, max_polls: int = 20,
                interval_s: float = 30.0, sleep: Callable[[float], None] = time.sleep,
                clock: Callable[[], float] = time.time,
                stale_after_s: int = DEFAULT_STALE_AFTER_S) -> dict[str, Any]:
    """Poll at most max_polls times. Returns the last observation.

    Transient UNAVAILABLE results are re-polled within the same bound; the
    caller keeps the lease for anything that is not terminal.
    """
    if type(max_polls) is not int or not 1 <= max_polls <= 120:
        raise ValueError("max_polls must be 1..120")
    last: dict[str, Any] = {"state": "UNAVAILABLE", "reason": "not_polled"}
    for attempt in range(max_polls):
        last = observe_once(api, agent_id, run_id, now=clock(), stale_after_s=stale_after_s)
        last["polls"] = attempt + 1
        if last["state"] not in ("IN_PROGRESS", "UNAVAILABLE"):
            return last
        if attempt + 1 < max_polls:
            sleep(interval_s)
    return last


def reconcile_dispatching(api: Any, agent_id: str) -> dict[str, Any]:
    """Resolve a DISPATCHING lease after an ambiguous create, without POSTing.

    Cursor v1 rejects a re-POST of the same agentId with 409 agent_id_conflict,
    so a lost response is resolved by reading the deterministic agent id.
    """
    if not isinstance(agent_id, str) or not AGENT.fullmatch(agent_id):
        return {"state": "UNKNOWN", "reason": "invalid_agent_identity"}
    try:
        agent = api.get_json(f"/v1/agents/{agent_id}")
    except CursorReadError as exc:
        if exc.status == 404:
            return {"state": "AGENT_ABSENT", "reason": "provider_has_no_agent_for_request"}
        return {"state": "UNAVAILABLE", "reason": "provider_read_failed", "status": exc.status}
    if agent.get("id") != agent_id:
        return {"state": "AMBIGUOUS", "reason": "provider_identity_mismatch"}
    run_id = agent.get("latestRunId")
    if not isinstance(run_id, str) or not RUN.fullmatch(run_id):
        return {"state": "AMBIGUOUS", "reason": "agent_without_verifiable_run"}
    return {"state": "RUN_FOUND", "run_id": run_id, "agent_status": agent.get("status")}


def provider_quiescent(api: Any, agent_id: str) -> dict[str, Any]:
    """True only if the agent is absent, or not ACTIVE with a terminal latest run."""
    found = reconcile_dispatching(api, agent_id)
    if found["state"] == "AGENT_ABSENT":
        return {"quiescent": True, "reason": "agent_absent"}
    if found["state"] != "RUN_FOUND":
        return {"quiescent": False, "reason": found["reason"]}
    try:
        run = api.get_json(f"/v1/agents/{agent_id}/runs/{found['run_id']}")
    except CursorReadError:
        return {"quiescent": False, "reason": "latest_run_unreadable"}
    terminal = run.get("status") in TERMINAL and found.get("agent_status") != "ACTIVE"
    return {"quiescent": terminal, "reason": "terminal" if terminal else "run_active_or_unknown",
            "run_status": run.get("status")}


_GH_RUN = re.compile(r"run-([1-9][0-9]*)\Z")


def github_actions_run_id(run_id: Any) -> int | None:
    """Legacy OpenHands leases record a GitHub Actions run as run-<digits>."""
    match = _GH_RUN.fullmatch(run_id) if isinstance(run_id, str) else None
    return int(match.group(1)) if match else None
