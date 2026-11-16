#!/usr/bin/env python3
"""Offline, fail-closed transition policy for the owner-approved Haversine 3-issue pilot.

NOT a live launcher or authorization source. GitHub evidence must be authenticated,
fresh and independently collected by a protected workflow before this is used.
"""
from dataclasses import dataclass

QUEUE = ((216, "docs/compatibility.md"),
         (217, "docs/examples/v2-consumers.md"),
         (226, "docs/examples/v2-coding-assistants.md"))


@dataclass(frozen=True)
class Evidence:
    issue: int
    target: str
    draft_pr: int
    pr_state: str
    is_draft: bool
    exact_head: bool
    changed_paths: tuple[str, ...]
    ci: str
    security: str
    provenance_verified: bool
    lease_released: bool


def next_step(completed, *, inventory_verified=False, owner_run_approved=False,
              budget_verified=False, writer_idle=False, default_head_stable=False,
              collisions_absent=False, state_durable=False):
    """Return a decision, never execute or authorize an agent."""
    if not owner_run_approved:
        return ("STOP", "owner_authority_missing")
    if not inventory_verified or not default_head_stable or not collisions_absent:
        return ("STOP", "github_evidence_incomplete")
    if not state_durable:
        return ("STOP", "replay_protection_unverified")
    if not budget_verified:
        return ("STOP", "shared_budget_unverified")
    if not writer_idle:
        return ("WAIT", "writer_or_lease_busy")
    if not isinstance(completed, (tuple, list)) or len(completed) > len(QUEUE):
        return ("STOP", "invalid_history")
    seen_prs = set()
    for index, entry in enumerate(completed):
        if not isinstance(entry, Evidence):
            return ("STOP", "invalid_evidence")
        issue, path = QUEUE[index]
        if entry.issue != issue or entry.target != path:
            return ("STOP", "out_of_order_or_wrong_target")
        if not isinstance(entry.draft_pr, int) or entry.draft_pr <= 0 or entry.draft_pr in seen_prs:
            return ("STOP", "duplicate_or_missing_pr")
        seen_prs.add(entry.draft_pr)
        if (entry.pr_state != "open" or not entry.is_draft
                or not entry.exact_head or entry.changed_paths != (path,)
                or entry.ci != "SUCCESS" or entry.security != "SUCCESS"
                or not entry.provenance_verified or not entry.lease_released):
            return ("STOP", "previous_pr_not_verified")
    if len(completed) == len(QUEUE):
        return ("COMPLETE", "three_verified_draft_prs_not_merged")
    return ("NEXT_CANDIDATE", str(QUEUE[len(completed)][0]))


def self_test():
    ready = dict(inventory_verified=True, owner_run_approved=True,
                 budget_verified=True, writer_idle=True, default_head_stable=True,
                 collisions_absent=True, state_durable=True)
    entries = [Evidence(n, p, 300 + i, "open", True, True, (p,), "SUCCESS",
                        "SUCCESS", True, True) for i, (n, p) in enumerate(QUEUE)]
    assert next_step([], **ready) == ("NEXT_CANDIDATE", "216")
    assert next_step(entries[:1], **ready) == ("NEXT_CANDIDATE", "217")
    assert next_step(entries[:2], **ready) == ("NEXT_CANDIDATE", "226")
    assert next_step(entries, **ready)[0] == "COMPLETE"
    for key in ready:
        bad = {**ready, key: False}
        assert next_step(entries[:1], **bad)[0] != "NEXT_CANDIDATE", key
    from dataclasses import replace
    for bad in (replace(entries[0], ci="PENDING"),
                replace(entries[0], security="SKIPPED"),
                replace(entries[0], exact_head=False),
                replace(entries[0], changed_paths=("package.json",)),
                replace(entries[0], lease_released=False),
                replace(entries[0], provenance_verified=False),
                replace(entries[0], is_draft=False)):
        assert next_step([bad], **ready)[0] == "STOP"
    assert next_step([entries[1]], **ready)[0] == "STOP"
    assert next_step([entries[0], replace(entries[1], draft_pr=entries[0].draft_pr)], **ready)[0] == "STOP"
    assert next_step(entries + entries[:1], **ready)[0] == "STOP"
    print("PASS: 3-issue transition policy and negative fixtures (offline only)")


if __name__ == "__main__":
    self_test()
