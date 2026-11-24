#!/usr/bin/env python3
"""#164 offline admission boundary; NOT wired to live model execution.

A trusted workflow must authenticate the snapshot and writer identity. A
caller-provided JSON lease is not authorization. No network, model or writes.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any

from github_ref_lease import check_state, agent_id_for, LeaseError

ISSUES = (216, 217, 226)
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


def validate_lease_snapshot(snapshot: dict[str, Any], ctx: Context, *,
                            observed_lease_sha: str = '',
                            authenticated_ref: bool = False,
                            exclusive_writer_verified: bool = False,
                            credential_path_verified: bool = False) -> str:
    """Necessary preconditions only; never returns a launch capability.

    The observed ref SHA must come from a fresh authenticated read and match
    the independently pinned lease commit. This comparison alone does NOT
    prevent a subsequent ref advance (TOCTOU): the trusted workflow must
    establish an exclusive writer and revalidate immediately before dispatch.
    All three evidence flags must be supplied by an independently trusted
    live verifier, not by issue text, agent output, or caller-supplied JSON.
    """
    if not (authenticated_ref and exclusive_writer_verified and credential_path_verified):
        raise AdmissionDenied("operational_security_not_verified")
    if (not isinstance(ctx.expected_lease_sha, str)
            or not SHA.fullmatch(ctx.expected_lease_sha)
            or not isinstance(observed_lease_sha, str)
            or not SHA.fullmatch(observed_lease_sha)
            or observed_lease_sha != ctx.expected_lease_sha):
        raise AdmissionDenied("lease_ref_sha_missing_or_stale")
    if type(ctx.issue) is not int or ctx.issue not in ISSUES:
        raise AdmissionDenied("issue_out_of_scope")
    if not isinstance(ctx.target_sha, str) or not SHA.fullmatch(ctx.target_sha):
        raise AdmissionDenied("target_sha_invalid")
    if not isinstance(ctx.workflow_run_id, str) or not re.fullmatch(
            r"[1-9][0-9]{0,19}", ctx.workflow_run_id):
        raise AdmissionDenied("workflow_run_id_invalid")
    allowed_ids = {f"openhands-164-issue-{ctx.issue}"}
    if ctx.issue == 217:
        allowed_ids.add("openhands-164-issue-217-recovery-8")
    if ctx.request_id not in allowed_ids:
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
    from test_github_ref_lease import MemoryGitRef
    from dataclasses import replace
    store = MemoryGitRef()
    ctx = Context(216, "openhands-164-issue-216", "a" * 40, "123456", "b" * 40)
    assert Controller(store).acquire(ctx.request_id, f"{REPO}/issues/216") == "ACQUIRED"
    snapshot = store.read().state
    flags = dict(authenticated_ref=True, exclusive_writer_verified=True,
                 credential_path_verified=True, observed_lease_sha="b" * 40)
    assert validate_lease_snapshot(snapshot, ctx, **flags).startswith("LEASE_PRECONDITIONS")
    cases = [
        (snapshot, ctx, {**flags, "exclusive_writer_verified": False}),
        (snapshot, ctx, {**flags, "authenticated_ref": False}),
        (snapshot, ctx, {**flags, "credential_path_verified": False}),
        (snapshot, replace(ctx, issue=217), flags),
        (snapshot, replace(ctx, target_sha="invalid"), flags),
        (snapshot, replace(ctx, workflow_run_id="0"), flags),
        (snapshot, replace(ctx, expected_lease_sha="c" * 40), flags),
        (snapshot, ctx, {**flags, "observed_lease_sha": "c" * 40}),
        (snapshot, ctx, {**flags, "observed_lease_sha": ""}),
        ({**snapshot, "phase": "DISPATCHING"}, ctx, flags),
        ({**snapshot, "request_id": "openhands-164-issue-217"}, ctx, flags),
        ({**snapshot, "source_issue_url": f"{REPO}/issues/217"}, ctx, flags),
        ({**snapshot, "run_id": "run-old"}, ctx, flags),
    ]
    for state, context, evidence in cases:
        try:
            validate_lease_snapshot(state, context, **evidence)
        except AdmissionDenied:
            continue
        raise AssertionError("unsafe lease admission accepted")
    print("PASS: #164 strict lease preconditions and negative cases (offline only)")


if __name__ == "__main__":
    self_test()
