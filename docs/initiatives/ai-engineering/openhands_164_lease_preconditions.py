#!/usr/bin/env python3
"""#164 offline admission boundary; NOT wired to live model execution.

A trusted workflow must authenticate the snapshot and writer identity. A
caller-provided JSON lease is not authorization. No network, model or writes.
"""
from __future__ import annotations

from dataclasses import replace

from openhands_164_lease_admission_scope import (
    AdmissionDenied,
    Context,
    DOC_ISSUES,
    REPO,
    validate_lease_snapshot,
)

ISSUES = DOC_ISSUES


def self_test() -> None:
    from github_ref_lease import Controller
    from test_github_ref_lease import MemoryGitRef

    store = MemoryGitRef()
    ctx = Context(216, "openhands-164-issue-216", "a" * 40, "123456", "b" * 40)
    assert Controller(store).acquire(ctx.request_id, f"{REPO}/issues/216") == "ACQUIRED"
    snapshot = store.read().state
    flags = dict(
        authenticated_ref=True,
        exclusive_writer_verified=True,
        credential_path_verified=True,
        observed_lease_sha="b" * 40,
    )
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