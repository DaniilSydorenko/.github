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
TOKENS = ("inputTokens", "outputTokens", "cacheWriteTokens",
          "cacheReadTokens", "totalTokens")


class CursorReadError(RuntimeError):
    pass


class LiveCursorReadOnly:
    """Deliberately exposes GET only: no POST, write, billing, or agent creation."""

    def __init__(self, key: str):
        if not isinstance(key, str) or not key:
            raise CursorReadError("Cursor API key unavailable")
        self._key = key

    def get_json(self, path: str, params: dict | None = None) -> dict:
        if not path.startswith("/v1/agents") or "?" in path or ".." in path:
            raise CursorReadError("unapproved Cursor API path")
        suffix = ("?" + urlencode(params)) if params else ""
        req = Request("https://api.cursor.com" + path + suffix,
                      headers={"Authorization": "Bearer " + self._key,
                               "Accept": "application/json"},
                      method="GET")
        try:
            with urlopen(req, timeout=12) as response:
                obj = json.load(response)
        except HTTPError as exc:
            raise CursorReadError(f"Cursor HTTP {exc.code} (body withheld)") from None
        except (URLError, TimeoutError, OSError, ValueError, UnicodeError):
            raise CursorReadError("Cursor transport/response unknown") from None
        if not isinstance(obj, dict):
            raise CursorReadError("Cursor payload not an object")
        return obj


def from_environment() -> LiveCursorReadOnly:
    key = os.environ.get("CURSOR_API_KEY")
    if not key:
        raise CursorReadError("CURSOR_API_KEY unavailable")
    return LiveCursorReadOnly(key)


def global_run_preflight(api, *, global_account_scope_verified: bool,
                         max_pages: int = 10) -> dict:
    """Return STOP/BUSY/CLEAR observational result; never authorizes dispatch.

    Caller must attest full account scope independently of any untrusted Issue.
    Agent status ACTIVE prevents another run; IDLE needs latest run terminal.
    """
    if global_account_scope_verified is not True:
        return {"status": "STOP", "reason": "account_scope_unverified",
                "can_launch": False}
    if type(max_pages) is not int or max_pages < 1 or max_pages > 20:
        return {"status": "STOP", "reason": "invalid_page_budget", "can_launch": False}
    seen_agents, seen_cursors = set(), set()
    cursor = None
    try:
        for _ in range(max_pages):
            params = {"limit": "100"}
            if cursor:
                params["cursor"] = cursor
            page = api.get_json("/v1/agents", params)
            items = page.get("items")
            if not isinstance(items, list):
                raise CursorReadError("agent list not an array")
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
                    raise CursorReadError("unknown agent status")
                latest = agent.get("latestRunId")
                if not isinstance(latest, str) or not RUN.fullmatch(latest):
                    raise CursorReadError("latest run unavailable")
                run = api.get_json(f"/v1/agents/{ident}/runs/{latest}")
                if run.get("agentId") != ident or run.get("id") != latest:
                    raise CursorReadError("run identity mismatch")
                if run.get("status") not in TERMINAL:
                    return {"status": "BUSY", "reason": "cursor_run_not_terminal",
                            "can_launch": False, "active_agent": ident}
            cursor = page.get("nextCursor")
            if cursor is None:
                return {"status": "CLEAR", "reason": "no_active_cursor_agents",
                        "can_launch": False, "observed_agents": len(seen_agents)}
            if not isinstance(cursor, str) or not cursor or cursor in seen_cursors:
                raise CursorReadError("invalid/cyclic pagination")
            seen_cursors.add(cursor)
        raise CursorReadError("pagination incomplete")
    except (CursorReadError, KeyError, TypeError):
        return {"status": "STOP", "reason": "cursor_inventory_incomplete",
                "can_launch": False}


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
