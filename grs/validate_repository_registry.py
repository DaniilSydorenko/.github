#!/usr/bin/env python3
"""Validate the Engineering Governance v1 repository discovery registry.

This validator is intentionally local/read-only. It validates structure and the
no-duplicate-status rule; it does not mutate repositories and is not wired into
required CI until the owner approves cross-repository enforcement.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

EXPECTED_REPOS = {
    "DaniilSydorenko/.github",
    "DaniilSydorenko/autopilot-control-plane",
    "DaniilSydorenko/listing-kit",
    "DaniilSydorenko/career-intelligence",
    "DaniilSydorenko/engineering-handbook",
    "DaniilSydorenko/engineering-labs",
    "DaniilSydorenko/haversine-geolocation",
}

ALLOWED_CLASSES = {
    "profile",
    "oss-library",
    "product",
    "engineering-labs",
    "knowledge",
    "platform",
    "historical",
}

FORBIDDEN_STATUS_KEYS = {
    "progress",
    "percentage",
    "percent",
    "status",
    "completion",
    "current_sha",
    "head_sha",
    "ci_status",
    "current_pr",
    "runtime_state",
}


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "governance/repository-registry.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"cannot read registry: {exc}")

    if not isinstance(data, dict):
        return fail("registry root must be an object")

    if data.get("schema_version") != 1:
        return fail("schema_version must equal 1")

    repos = data.get("repositories")
    if not isinstance(repos, list):
        return fail("repositories must be a list")

    if not all(isinstance(item, dict) for item in repos):
        return fail("every repository record must be an object")

    names = [item.get("repository") for item in repos]
    if not all(isinstance(name, str) and name for name in names):
        return fail("every repository name must be a non-empty string")
    if len(names) != len(set(names)):
        return fail("repository names must be unique")

    if set(names) != EXPECTED_REPOS:
        missing = sorted(EXPECTED_REPOS - set(names))
        extra = sorted(set(names) - EXPECTED_REPOS)
        return fail(f"registry scope mismatch; missing={missing}, extra={extra}")

    for item in repos:
        if not isinstance(item, dict):
            return fail("every repository record must be an object")
        if not isinstance(item.get("default_branch"), str) or not item["default_branch"]:
            return fail(f"{item.get('repository')}: default_branch is required")
        if item.get("grs_class") not in ALLOWED_CLASSES:
            return fail(f"{item.get('repository')}: unknown grs_class")
        discovery = item.get("discovery")
        if not isinstance(discovery, dict):
            return fail(f"{item.get('repository')}: discovery object is required")
        if not isinstance(discovery.get("roadmap"), str) or not discovery["roadmap"]:
            return fail(f"{item.get('repository')}: discovery.roadmap is required")

    forbidden = sorted(FORBIDDEN_STATUS_KEYS.intersection(set(walk_keys(data))))
    if forbidden:
        return fail(
            "registry must not duplicate mutable status/runtime state; "
            f"forbidden keys present: {', '.join(forbidden)}"
        )

    print("PASS: repository discovery registry is structurally valid and status-free")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
