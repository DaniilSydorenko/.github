"""Reviewed registry of Cursor-managed tasks (CONFIGURATION, not runtime evidence).

Adding a task here is the owner's approval of its scope: it lands only through a
reviewed PR on protected main. Runtime facts (Issue state, default SHA, open
PRs, CI) are always re-read live; nothing in this file is treated as observed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from openhands_issue_contract import PATH as ISSUE_220_PATH

OWNER = "DaniilSydorenko"
CONTROL_REPO = "DaniilSydorenko/.github"
HAVERSINE = "DaniilSydorenko/haversine-geolocation"
# Required check-run names on the exact PR head. "Test and build" runs
# npm run quality, typecheck, test and build in the target repository's own CI
# (unprivileged GitHub runner, none of our credentials).
HAVERSINE_REQUIRED_CHECKS = ("Test and build", "Gitleaks")
DEFAULT_MODEL = "composer-2"


@dataclass(frozen=True)
class CursorTask:
    repository: str
    issue: int
    order: int
    allowed_paths: tuple[str, ...]
    required_checks: tuple[str, ...]
    default_branch: str = "master"
    model: str = DEFAULT_MODEL
    # sequential_handoff vocabulary: only ui_low_risk may run without an extra
    # owner gate; anything else stops at OWNER_GATE.
    scope: str = "ui_low_risk"
    dependencies: tuple[int, ...] = ()

    @property
    def issue_url(self) -> str:
        return f"https://github.com/{self.repository}/issues/{self.issue}"


TASKS: tuple[CursorTask, ...] = (
    CursorTask(HAVERSINE, 220, 1, (ISSUE_220_PATH,), HAVERSINE_REQUIRED_CHECKS),
)


def validate_registry(tasks: tuple[CursorTask, ...] = TASKS) -> None:
    seen, orders = set(), set()
    for t in tasks:
        key = (t.repository, t.issue)
        if key in seen or (t.repository, t.order) in orders:
            raise ValueError("duplicate task or order")
        seen.add(key)
        orders.add((t.repository, t.order))
        if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", t.repository)
                or t.issue <= 0 or t.order <= 0 or not t.allowed_paths
                or not t.required_checks or t.scope not in ("ui_low_risk", "ui_owner_gated")
                or any(p.startswith("/") or ".." in p.split("/") for p in t.allowed_paths)):
            raise ValueError(f"invalid task {key}")
        if any(d == t.issue for d in t.dependencies):
            raise ValueError("task depends on itself")


def task_for(repository: str, issue: int) -> CursorTask | None:
    for t in TASKS:
        if t.repository == repository and t.issue == issue:
            return t
    return None


def task_for_issue_number(issue: int) -> CursorTask | None:
    matches = [t for t in TASKS if t.issue == issue]
    return matches[0] if len(matches) == 1 else None


def queue_for(repository: str) -> list[CursorTask]:
    return sorted((t for t in TASKS if t.repository == repository), key=lambda t: t.order)


validate_registry()
