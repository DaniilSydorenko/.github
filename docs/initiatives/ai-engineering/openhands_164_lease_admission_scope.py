#!/usr/bin/env python3
"""Shared #164 admission scope and reserved-lease snapshot checks.

Imported by the lease admission adapter and live preconditions. This module is
not replaced by the CI #166 preconditions overlay, so registered code-task
issues stay in scope after overlay integration tests.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from github_ref_lease import LeaseError, agent_id_for, check_state

DOC_ISSUES = (216, 217, 226)
REPO = "https://github.com/DaniilSydorenko/haversine-geolocation"
SHA = re.compile(r"[0-9a-f]{40}\Z")


class AdmissionDenied(RuntimeError):
    pass


@dataclass(frozen=True)
class Context:
    issue: int
    request_id: str
    target_sha: str
    workflow_run_id: str
    expected_lease_sha: str


def all_issues() -> tuple[int, ...]:
    try:
        from openhands_164_code_task import registered_code_issues

        return DOC_ISSUES + registered_code_issues()
    except ImportError:
        return DOC_ISSUES


def allowed_request_ids(issue: int) -> set[str]:
    try:
        from openhands_164_code_task import admission_request_id, is_code_task_issue

        if is_code_task_issue(issue):
            return {admission_request_id(issue)}
    except ImportError:
        pass
    allowed = {f"openhands-164-issue-{issue}"}
    if issue == 217:
        allowed.add("openhands-164-issue-217-recovery-8")
        allowed.add("openhands-164-issue-217-correction-9")
    return allowed


def validate_lease_snapshot(
    snapshot: dict[str, Any],
    ctx: Context,
    *,
    observed_lease_sha: str = "",
    authenticated_ref: bool = False,
    exclusive_writer_verified: bool = False,
    credential_path_verified: bool = False,
) -> str:
    if not (authenticated_ref and exclusive_writer_verified and credential_path_verified):
        raise AdmissionDenied("operational_security_not_verified")
    if (
        not isinstance(ctx.expected_lease_sha, str)
        or not SHA.fullmatch(ctx.expected_lease_sha)
        or not isinstance(observed_lease_sha, str)
        or not SHA.fullmatch(observed_lease_sha)
        or observed_lease_sha != ctx.expected_lease_sha
    ):
        raise AdmissionDenied("lease_ref_sha_missing_or_stale")
    if type(ctx.issue) is not int or ctx.issue not in all_issues():
        raise AdmissionDenied("issue_out_of_scope")
    if not isinstance(ctx.target_sha, str) or not SHA.fullmatch(ctx.target_sha):
        raise AdmissionDenied("target_sha_invalid")
    if not isinstance(ctx.workflow_run_id, str) or not re.fullmatch(r"[1-9][0-9]{0,19}", ctx.workflow_run_id):
        raise AdmissionDenied("workflow_run_id_invalid")
    if ctx.request_id not in allowed_request_ids(ctx.issue):
        raise AdmissionDenied("request_identity_mismatch")
    try:
        check_state(snapshot)
    except (LeaseError, TypeError, AttributeError) as exc:
        raise AdmissionDenied("lease_state_invalid") from exc
    if snapshot["phase"] != "RESERVED":
        raise AdmissionDenied("lease_not_reserved")
    if snapshot["request_id"] != ctx.request_id:
        raise AdmissionDenied("lease_owned_by_other_request")
    if snapshot["agent_id"] != agent_id_for(ctx.request_id):
        raise AdmissionDenied("agent_identity_mismatch")
    if snapshot.get("source_issue_url") != f"{REPO}/issues/{ctx.issue}":
        raise AdmissionDenied("source_issue_mismatch")
    if snapshot.get("pr_url") != f"{REPO}/issues/{ctx.issue}":
        raise AdmissionDenied("lease_target_mismatch")
    if snapshot.get("run_id") is not None:
        raise AdmissionDenied("unexpected_existing_run")
    return "LEASE_PRECONDITIONS_VERIFIED_NOT_LIVE_AUTHORIZATION"


def self_test() -> None:
    from github_ref_lease import Controller
    from openhands_164_code_task import CodeTaskSpec, TRUSTED_CODE_TASKS, admission_request_id
    from test_github_ref_lease import MemoryGitRef

    TRUSTED_CODE_TASKS[99164] = CodeTaskSpec(("src/x.ts", "spec/x.spec.ts"), "goal")
    try:
        assert 99164 in all_issues()
        store = MemoryGitRef()
        rid = admission_request_id(99164)
        assert Controller(store).acquire(rid, f"{REPO}/issues/99164") == "ACQUIRED"
        snap = store.read().state
        head = store.read().sha
        ctx = Context(99164, rid, head, "42", head)
        validate_lease_snapshot(
            snap,
            ctx,
            observed_lease_sha=head,
            authenticated_ref=True,
            exclusive_writer_verified=True,
            credential_path_verified=True,
        )
    finally:
        TRUSTED_CODE_TASKS.pop(99164, None)
    print("PASS: #164 admission scope includes registered code tasks (overlay-safe)")


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["--self-test"]:
        self_test()
    else:
        sys.exit("Usage: openhands_164_lease_admission_scope.py [--self-test]")