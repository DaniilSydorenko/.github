"""Offline, provenance-conscious Issue↔PR semantic reconciliation (Issue #117).

This classifies ONE owner-authorized task and its *bounded, attested* PR inventory.
It does NOT infer semantic equivalence from titles, age, filenames or green CI.
Caller-supplied reviewer attestations are hypotheses, not GitHub/provider proof.
Every result is ADVISORY, launched=False, execution_authorized=False.
"""

from __future__ import annotations

import re
from typing import Any

SHA = re.compile(r"[0-9a-f]{40}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
RELATIONS = {
    "EXACT_SAME_OUTCOME", "PROPOSED_NOT_ACCEPTED", "PARTIAL",
    "SUPERSEDED_BY_OWNER", "UNRELATED", "INSUFFICIENT_EVIDENCE",
}
ACTIONS = {
    "STOP", "OWNER_GATE", "WAIT_DEPENDENCY", "REUSE_EXISTING_PR",
    "READY_FOR_OWNER_DISPATCH", "NO_READY_WORK",
}


def _result(action: str, reason: str, pr: int | None = None) -> dict[str, Any]:
    assert action in ACTIONS
    return {"action": action, "reason": reason, "selected_pr": pr,
            "advisory_only": True, "launched": False, "execution_authorized": False}


def _sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA.fullmatch(value))


def _paths(value: Any) -> bool:
    return (isinstance(value, list) and bool(value) and len(value) == len(set(
        x for x in value if isinstance(x, str))) and all(
        isinstance(x, str) and x and not x.startswith("/")
        and "\\" not in x and not any(piece in (".", "..") for piece in x.split("/"))
        for x in value))


def reconcile_one(evidence: dict[str, Any]) -> dict[str, Any]:
    """Deterministic semantic preflight; never call as final launch authorization.

    Expected PRs already observed through trusted_github_evidence.py, and
    reviewer asserted relevance/relationships separately. Exactly verified
    GitHub facts/owner decisions must be re-fetched before using the proposal.
    """
    if not isinstance(evidence, dict) or evidence.get("schema_version") != 1:
        return _result("STOP", "schema_missing_or_unknown")

    repo = evidence.get("repository")
    number = evidence.get("issue_number")
    if (not isinstance(repo, str) or not REPO.fullmatch(repo)
            or type(number) is not int or number <= 0
            or evidence.get("issue_url") != f"https://github.com/{repo}/issues/{number}"):
        return _result("STOP", "issue_identity_unknown")

    if evidence.get("inventory_complete") is not True or evidence.get(
            "semantic_attestations_complete") is not True:
        return _result("STOP", "relevant_inventory_or_semantics_incomplete")
    if not _sha(evidence.get("default_sha")) or evidence.get("default_sha") != evidence.get(
            "observed_default_sha"):
        return _result("STOP", "default_branch_head_unverified_or_changed")
    if evidence.get("issue_state") != "open":
        # A closed Issue alone is NEVER proof of the claimed product outcome.
        return _result("STOP", "issue_closed_requires_accepted_outcome_proof")
    if evidence.get("permission") != "granted":
        return _result("OWNER_GATE", "domain_owner_permission_missing")
    if type(evidence.get("owner_gate")) is not bool:
        return _result("STOP", "owner_gate_unknown")
    if evidence["owner_gate"]:
        return _result("OWNER_GATE", "owner_decision_open")
    if evidence.get("writer") not in ("idle", "active"):
        return _result("STOP", "writer_state_unknown")
    if evidence["writer"] == "active":
        return _result("WAIT_DEPENDENCY", "active_domain_writer")
    if not _paths(evidence.get("proposed_paths")):
        return _result("STOP", "scoped_paths_unverified")

    items = evidence.get("prs")
    if not isinstance(items, list) or len(items) > 20:
        return _result("STOP", "pr_inventory_unbounded_or_unknown")
    lookup: dict[int, dict[str, Any]] = {}
    for p in items:
        if not isinstance(p, dict):
            return _result("STOP", "invalid_pr_record")
        n = p.get("number")
        if type(n) is not int or n <= 0 or n in lookup:
            return _result("STOP", "duplicate_or_invalid_pr_number")
        if p.get("url") != f"https://github.com/{repo}/pull/{n}":
            return _result("STOP", "cross_repository_or_invalid_pr")
        if p.get("state") not in ("open", "closed") or type(p.get("merged")) is not bool:
            return _result("STOP", "pr_state_unknown")
        if not _sha(p.get("head_sha")) or p.get("head_sha") != p.get("observed_head_sha"):
            return _result("STOP", "pr_head_unknown_or_stale")
        if not _sha(p.get("base_sha")) or p.get("base_sha") != p.get("observed_base_sha"):
            return _result("STOP", "pr_base_unknown_or_stale")
        if p.get("changed_paths_complete") is not True or not _paths(p.get("changed_paths")):
            return _result("STOP", "changed_paths_unverified")
        if p.get("relation") not in RELATIONS or p.get("reviewer_confirmed") is not True:
            return _result("STOP", "semantic_relation_unverified")
        if p["relation"] == "INSUFFICIENT_EVIDENCE":
            return _result("STOP", "semantic_relation_insufficient")
        if type(p.get("owner_gate")) is not bool or type(p.get("writer_active")) is not bool:
            return _result("STOP", "pr_owner_or_writer_unknown")
        if p["merged"] and p["state"] != "closed":
            return _result("STOP", "contradictory_pr_state")
        if p.get("stack_parent") is not None and (
                type(p["stack_parent"]) is not int or p["stack_parent"] == n):
            return _result("STOP", "invalid_stack_parent")
        if p["relation"] in ("EXACT_SAME_OUTCOME", "SUPERSEDED_BY_OWNER") and p["merged"]:
            if (not _sha(p.get("accepted_commit")) or p.get("accepted_on_default") is not True
                    or p.get("accepted_proof") not in (
                        f"https://github.com/{repo}/pull/{n}",
                        f"https://github.com/{repo}/commit/{p.get('accepted_commit')}")):
                return _result("STOP", "merged_claim_not_accepted_proof")
        lookup[n] = p

    proposed = set(evidence["proposed_paths"])
    for p in items:
        if p["relation"] == "SUPERSEDED_BY_OWNER":
            if p.get("owner_supersession_approved") is not True:
                return _result("OWNER_GATE", "supersession_owner_proof_missing", p["number"])
            if p["merged"]:
                return _result("NO_READY_WORK", "owner_accepted_superseding_outcome", p["number"])
            return _result("WAIT_DEPENDENCY", "superseding_pr_not_accepted", p["number"])

    matching = [p for p in items if p["relation"] in (
        "EXACT_SAME_OUTCOME", "PROPOSED_NOT_ACCEPTED", "PARTIAL")]
    merged_matches = [p for p in matching if p["merged"]]
    for p in merged_matches:
        # A merged, explicitly attested same-outcome PR still needs proof of
        # accepted product semantics and default-branch containment.
        if p["relation"] == "EXACT_SAME_OUTCOME":
            return _result("NO_READY_WORK", "owner_attested_accepted_outcome", p["number"])
        return _result("STOP", "merged_partial_work_requires_reconciliation", p["number"])
    open_matches = [p for p in matching if p["state"] == "open"]
    if len(open_matches) > 1:
        return _result("STOP", "multiple_competing_same_outcome_prs")
    if open_matches:
        p = open_matches[0]
        if p["writer_active"]:
            return _result("WAIT_DEPENDENCY", "existing_pr_has_active_writer", p["number"])
        if p["owner_gate"]:
            return _result("OWNER_GATE", "existing_pr_requires_owner", p["number"])
        parent = p.get("stack_parent")
        if parent is not None:
            ancestor = lookup.get(parent)
            if ancestor is None or not ancestor["merged"] or ancestor.get("accepted_on_default") is not True:
                return _result("WAIT_DEPENDENCY", "stack_parent_not_accepted", p["number"])
        return _result("REUSE_EXISTING_PR", "existing_pr_before_new_code", p["number"])

    # Even an attested UNRELATED PR may collide on files; independent scope
    # requires non-overlap, not merely an assertion in a title or comment.
    for p in items:
        if p["state"] == "open" and (
                proposed.intersection(p["changed_paths"]) or p["stack_parent"] is not None):
            return _result("WAIT_DEPENDENCY", "open_pr_path_or_stack_overlap", p["number"])
        if p["state"] == "open" and (p["writer_active"] or p["owner_gate"]):
            # No global freeze: an unrelated owner-gated PR blocks only if
            # overlap/dependency has already been demonstrated above.
            continue

    return _result("READY_FOR_OWNER_DISPATCH", "one_independent_leaf_candidate_only")
