"""Sanitized GET-only Cursor Cloud visibility probe. NO agent/model launch.

A successful API observation does NOT establish account-wide permission scope,
model billing safety, absence of alternate launch paths or an atomic lock.
Do not put agent IDs, credentials or provider payloads in public GH logs.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from cursor_readonly import CursorReadError, LiveCursorReadOnly

KNOWN = frozenset({"ACTIVE", "IDLE", "ARCHIVED"})


def observe(api: Any, *, max_pages: int = 5) -> dict[str, Any]:
    """Bounded paginated GET observation; never returns launch authority."""
    result = {"status": "STOP", "reason": "unobserved",
              "model_runs_started": 0, "read_only": True,
              "account_scope_verified": False, "billing_verified": False,
              "execution_authorized": False}
    if type(max_pages) is not int or max_pages < 1 or max_pages > 10:
        return {**result, "reason": "invalid_page_budget"}
    agents, cursors = set(), set()
    cursor = None
    active = idle = archived = 0
    try:
        for _ in range(max_pages):
            params = {"limit": "100"}
            if cursor is not None:
                params["cursor"] = cursor
            page = api.get_json("/v1/agents", params)
            items = page.get("items")
            if not isinstance(items, list) or len(items) > 100:
                raise CursorReadError("invalid page")
            for item in items:
                if not isinstance(item, dict):
                    raise CursorReadError("invalid item")
                identity, status = item.get("id"), item.get("status")
                if (not isinstance(identity, str) or not identity.startswith("bc-")
                        or identity in agents or status not in KNOWN):
                    raise CursorReadError("malformed or duplicate agent")
                agents.add(identity)
                if status == "ACTIVE":
                    active += 1
                elif status == "IDLE":
                    idle += 1
                else:
                    archived += 1
            cursor_next = page.get("nextCursor")
            if cursor_next is None:
                return {**result, "status": "OBSERVED",
                        "reason": "api_inventory_visible_not_account_verified",
                        "visible_active_agents": active,
                        "visible_idle_agents": idle,
                        "visible_archived_agents": archived,
                        "visible_agent_count": len(agents)}
            if not isinstance(cursor_next, str) or not cursor_next or cursor_next in cursors:
                raise CursorReadError("invalid pagination")
            cursors.add(cursor_next)
            cursor = cursor_next
        return {**result, "reason": "pagination_limit_reached"}
    except (CursorReadError, KeyError, TypeError, ValueError, AttributeError):
        return {**result, "reason": "api_unavailable_or_inventory_invalid"}


def main() -> int:
    key = os.environ.get("CURSOR_API_KEY")
    if not key:
        print(json.dumps({"status": "BLOCKED",
                          "reason": "cursor_key_not_configured",
                          "read_only": True, "model_runs_started": 0,
                          "execution_authorized": False,
                          "account_scope_verified": False}))
        return 2
    result = observe(LiveCursorReadOnly(key))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "OBSERVED" else 2


if __name__ == "__main__":
    sys.exit(main())
