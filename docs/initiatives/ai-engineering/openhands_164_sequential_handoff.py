#!/usr/bin/env python3
"""#164 deterministic three-issue handoff; offline only, never dispatches models.

A later trusted runner must supply independently authenticated per-issue
evidence. This module cannot acquire a lease, publish PRs, or authorize spend.
"""
from __future__ import annotations
from dataclasses import dataclass

QUEUE = (216, 217, 226)
EXPECTED_PATHS = (
    "docs/compatibility.md",
    "docs/examples/v2-consumers.md",
    "docs/examples/v2-coding-assistants.md",
)

@dataclass(frozen=True)
class IssueProof:
    issue: int
    path: str
    draft_pr: str
    exact_head: str
    checks_passed: bool
    security_passed: bool
    lease_released: bool
    authenticated: bool

def stop(reason: str) -> dict:
    return {"decision": "STOP", "reason": reason, "dispatch_authorized": False,
            "model_invoked": False, "github_write": False}

def next_issue(proofs: object) -> dict:
    """Compute next eligible issue, never a dispatch capability.

    Every previous issue must have one independently authenticated Draft PR,
    exact-head CI/security, and verified lease release before advancing.
    """
    if not isinstance(proofs, (tuple, list)):
        return stop("proof_inventory_untrusted")
    if len(proofs) > len(QUEUE):
        return stop("proof_inventory_too_long")
    seen_prs = set()
    for idx, proof in enumerate(proofs):
        if not isinstance(proof, IssueProof) or proof.issue != QUEUE[idx]:
            return stop("out_of_order_or_invalid_proof")
        if proof.path != EXPECTED_PATHS[idx]:
            return stop("unexpected_changed_path")
        if not proof.authenticated:
            return stop("proof_not_authenticated")
        if (not isinstance(proof.draft_pr, str)
                or not proof.draft_pr.startswith("https://github.com/DaniilSydorenko/haversine-geolocation/pull/")
                or not proof.draft_pr.rsplit("/", 1)[-1].isdigit()
                or proof.draft_pr in seen_prs):
            return stop("draft_pr_identity_unverified")
        seen_prs.add(proof.draft_pr)
        if (not isinstance(proof.exact_head, str) or len(proof.exact_head) != 40
                or any(ch not in "0123456789abcdef" for ch in proof.exact_head)):
            return stop("exact_head_unverified")
        if not proof.checks_passed or not proof.security_passed:
            return stop("exact_head_checks_or_security_incomplete")
        if not proof.lease_released:
            return stop("previous_lease_not_released")
    if len(proofs) == len(QUEUE):
        return stop("all_three_proofs_recorded_no_auto_merge")
    return {**stop("next_issue_candidate_not_live_authorization"),
            "next_issue": QUEUE[len(proofs)],
            "allowed_path": EXPECTED_PATHS[len(proofs)]}

def self_test() -> None:
    def good(i):
        return IssueProof(QUEUE[i], EXPECTED_PATHS[i],
            f"https://github.com/DaniilSydorenko/haversine-geolocation/pull/{400+i}",
            "a" * 40, True, True, True, True)
    assert next_issue([])["next_issue"] == 216
    assert next_issue([good(0)])["next_issue"] == 217
    assert next_issue([good(0), good(1)])["next_issue"] == 226
    assert next_issue([good(0), good(1), good(2)])["reason"] == "all_three_proofs_recorded_no_auto_merge"
    from dataclasses import replace
    cases = [
        ([good(1)], "out_of_order_or_invalid_proof"),
        ([replace(good(0), authenticated=False)], "proof_not_authenticated"),
        ([replace(good(0), checks_passed=False)], "exact_head_checks_or_security_incomplete"),
        ([replace(good(0), security_passed=False)], "exact_head_checks_or_security_incomplete"),
        ([replace(good(0), lease_released=False)], "previous_lease_not_released"),
        ([replace(good(0), path="README.md")], "unexpected_changed_path"),
        ([replace(good(0), exact_head="bad")], "exact_head_unverified"),
        ([good(0), replace(good(1), draft_pr=good(0).draft_pr)], "draft_pr_identity_unverified"),
        ([good(0), good(1), good(2), good(2)], "proof_inventory_too_long"),
    ]
    for proofs, reason in cases:
        outcome = next_issue(proofs)
        assert outcome["reason"] == reason, (outcome, reason)
        assert outcome["dispatch_authorized"] is False
    print("PASS: #164 sequential three-issue proof gate (offline; no dispatch)")

if __name__ == "__main__":
    self_test()
