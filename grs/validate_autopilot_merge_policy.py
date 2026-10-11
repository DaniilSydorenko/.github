#!/usr/bin/env python3
"""Validate the GitHub Autopilot merge-safety policy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED_CONDITIONS = {
    "current-run-explicit-authorization",
    "live-default-branch-inspected",
    "live-open-prs-inspected",
    "exact-head-sha-verified",
    "required-ci-green",
    "not-draft",
    "no-owner-gated-operation",
    "no-domain-ownership-conflict",
    "no-worker-roadmap-collision",
}

OWNER_ONLY = {
    "repository_visibility_change",
    "history_rewrite",
    "credential_rotation_or_revocation",
    "stable_release_publish",
}

FORBIDDEN = {
    "other_worker_roadmap",
    "merge_red_ci",
    "merge_changed_head",
    "force_update_without_expected_sha",
}


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("policy", type=Path)
    args = parser.parse_args()

    try:
        data = json.loads(args.policy.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"cannot read policy: {exc}")

    if not isinstance(data, dict):
        return fail("policy root must be an object")
    if data.get("version") != 1:
        return fail("policy version must equal 1")
    if data.get("mode") != "default-deny":
        return fail("policy mode must remain default-deny")

    merge_pr = data.get("merge_pr")
    if not isinstance(merge_pr, dict) or merge_pr.get("decision") != "conditional":
        return fail("merge_pr decision must remain conditional")

    conditions = merge_pr.get("required_conditions")
    if not isinstance(conditions, list) or not all(isinstance(value, str) for value in conditions):
        return fail("merge_pr.required_conditions must be a string list")

    missing_conditions = sorted(REQUIRED_CONDITIONS - set(conditions))
    if missing_conditions:
        return fail(f"merge policy is missing required conditions: {', '.join(missing_conditions)}")

    operations = data.get("operations")
    if not isinstance(operations, dict):
        return fail("operations object is required")

    for name in sorted(OWNER_ONLY):
        if operations.get(name) != "owner-only":
            return fail(f"{name} must remain owner-only")

    if operations.get("domain_product_code") != "domain-owner-only":
        return fail("domain_product_code must remain domain-owner-only")

    for name in sorted(FORBIDDEN):
        if operations.get(name) != "forbidden":
            return fail(f"{name} must remain forbidden")

    safe_scope = data.get("safe_merge_scope")
    if not isinstance(safe_scope, dict):
        return fail("safe_merge_scope object is required")

    allowed = safe_scope.get("allowed_when_all_conditions_hold")
    excluded = safe_scope.get("excluded")
    if not isinstance(allowed, list) or not allowed:
        return fail("safe_merge_scope must define at least one bounded allowed class")
    if not isinstance(excluded, list) or not excluded:
        return fail("safe_merge_scope must define exclusions")

    print("PASS: Autopilot merge policy is default-deny and owner gates remain protected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
