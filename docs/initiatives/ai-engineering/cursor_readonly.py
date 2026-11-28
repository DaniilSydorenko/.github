"""Read-only Cursor Cloud Agents v1 preflight. Never dispatches model work.

Account-scoped API key required. A repo-scoped key may not reveal every agent:
global exclusivity is therefore unproven unless account scope is attested.
GET does not count as a paid model run, but may count against API rate limits.
"""
from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

AGENT = re.compile(r"bc-[0-9a-fA-F-]{36}\Z")
RUN = re.compile(r"run-[0-9a-fA-F-]{36}\Z")
TERMINAL = {"FINISHED", "ERROR", "CANCELLED", "EXPIRED"}
ENUM = re.compile(r"[A-Z_]{1,40}\Z")
TOKENS = ("inputTokens", "outputTokens", "cacheWriteTokens",
          "cacheReadTokens", "totalTokens")


class CursorReadError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status  # HTTP status when the provider answered, else None


class LiveCursorReadOnly:
    """Deliberately exposes GET only: no POST, write, billing, or agent creation."""

    def __init__(self, key: str):
        if not isinstance(key, str) or not key:
            raise CursorReadError("Cursor API key unavailable")
        self._key = key

    def get_json(self, path: str, params: dict | None = None) -> dict:
        if ((not path.startswith("/v1/agents") and path not in ("/v1/models", "/v1/me"))
                or "?" in path or ".." in path):
            raise CursorReadError("unapproved Cursor API path")
        suffix = ("?" + urlencode(params)) if params else ""
        req = Request("https://api.cursor.com" + path + suffix,
                      headers={"Authorization": "Bearer " + self._key,
                               "Accept": "application/json"},
                      method="GET")
        # GET is read-only, so one retry after a transport failure is safe.
        # HTTP errors are definitive answers and are never retried.
        for attempt in (1, 2):
            try:
                with urlopen(req, timeout=20) as response:
                    obj = json.load(response)
                break
            except HTTPError as exc:
                raise CursorReadError(f"Cursor HTTP {exc.code} (body withheld)",
                                      status=exc.code) from None
            except (URLError, TimeoutError, OSError, ValueError, UnicodeError) as exc:
                if attempt == 2:
                    raise CursorReadError("Cursor transport/response unknown ("
                                          + type(exc).__name__ + ")") from None
        if not isinstance(obj, dict):
            raise CursorReadError("Cursor payload not an object")
        return obj


def from_environment() -> LiveCursorReadOnly:
    key = os.environ.get("CURSOR_API_KEY")
    if not key:
        raise CursorReadError("CURSOR_API_KEY unavailable")
    return LiveCursorReadOnly(key)


RUN_READ_CONCURRENCY = 6  # bounded parallel GETs; same evidence, same fail-closed result


def _read_run(api, ident: str, latest: str) -> dict:
    run = api.get_json(f"/v1/agents/{ident}/runs/{latest}")
    if not isinstance(run, dict) or run.get("agentId") != ident or run.get("id") != latest:
        raise CursorReadError("run identity mismatch")
    return run


def global_run_preflight(api, *, global_account_scope_verified: bool,
                         max_pages: int = 10,
                         concurrency: int = RUN_READ_CONCURRENCY) -> dict:
    """Return STOP/BUSY/CLEAR observational result; never authorizes dispatch.

    Caller must attest full account scope independently of any untrusted Issue.
    Agent status ACTIVE prevents another run; IDLE needs latest run terminal.
    Every page is validated in full first; the latest runs of its IDLE agents
    are then read with bounded concurrency (the slow part: one GET per agent)
    and judged in list order, so the result equals the sequential scan. No
    agent is skipped and nothing is cached: each call is a fresh observation.
    """
    from concurrent.futures import ThreadPoolExecutor

    if global_account_scope_verified is not True:
        return {"status": "STOP", "reason": "account_scope_unverified",
                "can_launch": False}
    if type(max_pages) is not int or max_pages < 1 or max_pages > 20:
        return {"status": "STOP", "reason": "invalid_page_budget", "can_launch": False}
    if type(concurrency) is not int or not 1 <= concurrency <= 16:
        return {"status": "STOP", "reason": "invalid_concurrency", "can_launch": False}
    seen_agents, seen_cursors = set(), set()
    cursor, phase = None, "list"
    try:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            for _ in range(max_pages):
                params = {"limit": "100"}
                if cursor:
                    params["cursor"] = cursor
                phase = "list"
                page = api.get_json("/v1/agents", params)
                items = page.get("items")
                if not isinstance(items, list):
                    raise CursorReadError("agent list not an array")
                idle: list[tuple[str, str]] = []
                for agent in items:
                    if not isinstance(agent, dict):
                        raise CursorReadError("invalid agent entry")
                    ident, status = agent.get("id"), agent.get("status")
                    if not isinstance(ident, str) or not AGENT.fullmatch(ident) or ident in seen_agents:
                        raise CursorReadError("unknown or duplicated agent identity")
                    seen_agents.add(ident)
                    if status == "ACTIVE":
                        return {"status": "BUSY", "reason": "cursor_agent_active",
                                "can_launch": False, "active_agent": ident}
                    if status == "ARCHIVED":
                        continue
                    if status != "IDLE":
                        raise CursorReadError("unknown agent status " + _enum(status))
                    latest = agent.get("latestRunId")
                    if not isinstance(latest, str) or not RUN.fullmatch(latest):
                        raise CursorReadError("latest run unavailable")
                    idle.append((ident, latest))
                phase = "run"
                futures = [pool.submit(_read_run, api, ident, latest) for ident, latest in idle]
                for (ident, _latest), future in zip(idle, futures):
                    run = future.result()  # a worker's CursorReadError fails the scan closed
                    if run.get("status") in ("CREATING", "RUNNING", "WAITING_FOR_BACKGROUND_WORK"):
                        return {"status": "BUSY", "reason": "cursor_run_not_terminal",
                                "can_launch": False, "active_agent": ident}
                    if run.get("status") not in TERMINAL:
                        raise CursorReadError("unknown run status " + _enum(run.get("status")))
                cursor = page.get("nextCursor")
                if cursor is None:
                    return {"status": "CLEAR", "reason": "no_active_cursor_agents",
                            "can_launch": False, "observed_agents": len(seen_agents)}
                if not isinstance(cursor, str) or not cursor or cursor in seen_cursors:
                    raise CursorReadError("invalid/cyclic pagination")
                seen_cursors.add(cursor)
            raise CursorReadError("pagination incomplete")
    except (CursorReadError, KeyError, TypeError, AttributeError) as exc:
        # Fail closed. detail carries only our own literals, an HTTP status
        # code or a provider enum: never a response body, id or key.
        return {"status": "STOP", "reason": "cursor_inventory_incomplete",
                "can_launch": False, "agents_checked": len(seen_agents), "phase": phase,
                "detail": str(exc) if isinstance(exc, CursorReadError)
                else type(exc).__name__}


def _enum(value: object) -> str:
    """Provider status for diagnostics, only if it is a plain enum token."""
    return value if isinstance(value, str) and ENUM.fullmatch(value) else "<non-enum>"


def model_ids(api) -> frozenset[str]:
    """Exact model ids from GET /v1/models (aliases deliberately excluded)."""
    try:
        items = api.get_json("/v1/models").get("items")
        if not isinstance(items, list) or not items:
            raise CursorReadError("model list empty or malformed")
        ids = [m.get("id") for m in items if isinstance(m, dict)]
        if len(ids) != len(items) or not all(isinstance(i, str) and i for i in ids):
            raise CursorReadError("model id malformed")
        return frozenset(ids)
    except (CursorReadError, AttributeError, TypeError):
        return frozenset()


def api_key_info_ok(api) -> bool:
    """GET /v1/me answers for this key. Proves a live key, NOT account-wide scope."""
    try:
        info = api.get_json("/v1/me")
    except CursorReadError:
        return False
    return isinstance(info.get("apiKeyName"), str) and isinstance(info.get("createdAt"), str)


def token_usage_readonly(api, agent_id: str, run_id: str) -> dict:
    """Observational token counters; never infer charged dollar cost = 0."""
    if not isinstance(agent_id, str) or not AGENT.fullmatch(agent_id):
        raise CursorReadError("invalid agent ID")
    if not isinstance(run_id, str) or not RUN.fullmatch(run_id):
        raise CursorReadError("invalid run ID")
    d = api.get_json(f"/v1/agents/{agent_id}/usage", {"runId": run_id})
    entries = d.get("runs")
    if not isinstance(entries, list) or len(entries) != 1 or entries[0].get("id") != run_id:
        raise CursorReadError("usage run mismatch")
    usage = entries[0].get("usage")
    if not isinstance(usage, dict):
        raise CursorReadError("usage missing")
    for k in TOKENS:
        if type(usage.get(k)) is not int or usage[k] < 0:
            raise CursorReadError("invalid token counter")
    if usage["totalTokens"] != sum(usage[k] for k in TOKENS[:4]):
        raise CursorReadError("token total mismatch")
    return {"agent_id": agent_id, "run_id": run_id,
            "tokens": {k: usage[k] for k in TOKENS},
            "charged_cost": "UNKNOWN"}
