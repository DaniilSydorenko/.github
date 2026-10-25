"""Read-only, fail-closed GitHub lease-ref protection audit.

This is NOT permission to dispatch Cursor or to modify branch settings.
A branch being "protected" by itself never establishes exclusive writership.
GitHub App writer identity and bypass/exceptions require independent proof.
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = "DaniilSydorenko/.github"
REF = "ai-eng-cursor-lease-v1"
API = "https://api.github.com/repos/" + REPO
SHA = re.compile(r"[0-9a-f]{40}\Z")


def outcome(status: str, reason: str) -> dict[str, Any]:
    return {
        "status": status, "reason": reason, "lease_ref": REF,
        "cursor_launch_authorized": False, "model_runs_started": 0,
        "git_writes": False, "owner_configuration_needed": status != "VERIFIED",
    }


def audit(branch: Any, protection: Any, *, approved_writer_app: str | None) -> dict:
    """Strict branch protection shape check: missing information is not green."""
    if not isinstance(branch, dict) or branch.get("name") != REF:
        return outcome("STOP", "branch_identity_not_verified")
    if branch.get("protected") is not True:
        return outcome("STOP", "lease_branch_unprotected")
    commit = branch.get("commit")
    if (not isinstance(commit, dict) or not isinstance(commit.get("sha"), str)
            or not SHA.fullmatch(commit["sha"])):
        return outcome("STOP", "lease_tip_unverified")
    if not isinstance(protection, dict):
        return outcome("STOP", "branch_protection_unavailable")
    for field in ("allow_force_pushes", "allow_deletions", "enforce_admins"):
        x = protection.get(field)
        if not isinstance(x, dict) or type(x.get("enabled")) is not bool:
            return outcome("STOP", "branch_protection_incomplete")
    if protection["allow_force_pushes"]["enabled"]:
        return outcome("STOP", "force_push_bypass_possible")
    if protection["allow_deletions"]["enabled"]:
        return outcome("STOP", "branch_deletion_possible")
    if not protection["enforce_admins"]["enabled"]:
        return outcome("STOP", "admin_bypass_not_disabled")

    # At this point non-forced CAS is protected from generic forced ref updates.
    # It is NOT exclusive until exactly the owner-approved GitHub App is the
    # sole authorized writer. Ordinary contents:write scopes cannot be enough.
    restrictions = protection.get("restrictions")
    if not isinstance(restrictions, dict):
        return outcome("STOP", "exclusive_writer_not_verified")
    users, teams, apps = (restrictions.get(x) for x in ("users", "teams", "apps"))
    if not isinstance(users, list) or not isinstance(teams, list) or not isinstance(apps, list):
        return outcome("STOP", "writer_restrictions_unavailable")
    if users or teams:
        return outcome("STOP", "human_or_team_push_bypass")
    if (not isinstance(approved_writer_app, str) or
            not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,99}", approved_writer_app)):
        return outcome("STOP", "approved_github_app_not_configured")
    if (len(apps) != 1 or not isinstance(apps[0], dict) or
            apps[0].get("slug") != approved_writer_app):
        return outcome("STOP", "exclusive_app_identity_not_verified")
    # "VERIFIED" is intentionally descriptive only. The owner must independently
    # review effective rulesets, admin ability to edit rules, actual token scope,
    # the app's bypass grants and all provider launch surfaces.
    return outcome("VERIFIED", "branch_rule_and_single_app_writer_observed_not_account_permission")


def public_readonly_probe(fetch_json, *, approved_writer_app=None) -> dict:
    """Caller-supplied GET transport; no POST/PATCH/PUT/DELETE methods needed."""
    try:
        branch = fetch_json(f"/branches/{REF}")
        if not isinstance(branch, dict) or branch.get("protected") is not True:
            return audit(branch, None, approved_writer_app=approved_writer_app)
        protection = fetch_json(f"/branches/{REF}/protection")
        return audit(branch, protection, approved_writer_app=approved_writer_app)
    except (ValueError, TypeError, KeyError, HTTPError, URLError, TimeoutError, OSError):
        return outcome("STOP", "github_protection_evidence_inaccessible")


class ReadOnlyGitHub:
    def __init__(self, token: str | None = None):
        self.token = token

    def get(self, path: str) -> dict:
        if path not in (f"/branches/{REF}", f"/branches/{REF}/protection"):
            raise ValueError("read-only allowlisted endpoint required")
        headers = {"Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        request = Request(API + path, method="GET", headers=headers)
        with urlopen(request, timeout=12) as response:
            value = json.load(response)
        if not isinstance(value, dict):
            raise ValueError("GitHub did not return an object")
        return value


def main() -> int:
    report = public_readonly_probe(
        ReadOnlyGitHub(os.getenv("GITHUB_TOKEN")).get,
        # No writer has been owner-approved/provisioned yet; env is not proof.
        approved_writer_app=None,
    )
    print(json.dumps(report, sort_keys=True))
    # Probe BLOCKED is an expected finding, not CI success.
    return 0 if report["status"] == "VERIFIED" else 2


if __name__ == "__main__":
    sys.exit(main())
