#!/usr/bin/env python3
"""Fail-closed validation for proposed PR/branch lifecycle contract."""
import json
import sys
from pathlib import Path

MERGE = {
    "explicit-current-run-authorization", "domain-owner-approval", "not-draft",
    "live-open-pr-and-base-ref-verified", "exact-head-sha-verified",
    "required-checks-green-on-exact-head", "no-unresolved-review-or-security-gate",
    "no-cross-worker-collision", "no-owner-gated-operation",
    "dependency-order-confirmed",
}
DELETE = {
    "explicit-current-run-authorization", "exact-branch-ref-and-sha",
    "not-default-or-protected", "no-open-pr", "no-active-worker-or-worktree",
    "no-release-tag-or-deployment-dependency", "no-stacked-pr-dependent",
    "merged-or-explicitly-abandoned-with-evidence",
    "recovery-record-with-ref-sha", "fresh-pre-delete-recheck",
}
FORBID_MERGE = {"red-or-missing-required-ci", "changed-head", "draft", "unknown-authority",
                "security-exception-without-owner-approval", "unreviewed-product-code",
                "stable-release-or-visibility-change"}
FORBID_DELETE = {"age-only", "no-open-pr-only", "unknown-ownership",
                 "unmerged-unreviewed", "active-dependency", "missing-recovery-record"}


def validate(data):
    if not isinstance(data, dict) or data.get("version") != 1 or data.get("mode") != "default-deny":
        raise ValueError("version 1 and default-deny required")
    if data.get("rollout") != "proposal-only-until-owner-approved-and-runtime-loading-proven":
        raise ValueError("rollout must remain proposal-only")
    for section, required, forbidden in (
        ("merge", MERGE, FORBID_MERGE),
        ("branch_deletion", DELETE, FORBID_DELETE),
    ):
        obj = data.get(section)
        if not isinstance(obj, dict):
            raise ValueError(f"{section}: missing object")
        for field, expected in (("required", required), ("forbidden", forbidden)):
            items = obj.get(field)
            if not isinstance(items, list) or any(not isinstance(x, str) for x in items):
                raise ValueError(f"{section}.{field}: expected string list")
            if len(items) != len(set(items)) or not expected.issubset(set(items)):
                raise ValueError(f"{section}.{field}: missing or duplicate safety gates")
    if data["branch_deletion"].get("mode") != "owner-or-domain-authorized-only":
        raise ValueError("branch deletion requires owner/domain authority")
    retention = data.get("retention", {})
    if not isinstance(retention, dict) or retention.get("open_or_draft_pr_branch") != "retain":
        raise ValueError("open/draft branches must be retained")
    if retention.get("unmerged_branch") != "retain-unless-explicit-owner-abandonment":
        raise ValueError("unmerged branch retention cannot be weakened")
    return True


if __name__ == "__main__":
    try:
        validate(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    except (ValueError, OSError, IndexError) as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)
    print("PASS: proposed lifecycle contract remains default-deny")
