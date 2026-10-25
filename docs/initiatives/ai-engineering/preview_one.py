"""Read-only one-task Cursor handoff preview, NOT a launch adapter (Issue #119).

Composes already accepted source-specific evidence_reconcile + decision_gate +
semantic_pr_reconcile. Assertions from file input are NOT authenticated live
GitHub/owner assertions; a real executor must re-fetch before every launch.
"""

from __future__ import annotations

from typing import Any

from evidence_reconcile import reconcile
from semantic_pr_reconcile import reconcile_one


def _reply(action: str, reason: str, *, issue: str | None = None,
           sha: str | None = None, pr: int | None = None) -> dict[str, Any]:
    return {
        "decision": action,
        "reason": reason,
        "issue": issue,
        "observed_sha": sha,
        "selected_pr": pr,
        "launched": False,
        "execution_authorized": False,
        "provider_called": False,
    }


def preview_one(bundle: dict[str, Any]) -> dict[str, Any]:
    """One task, bounded relevant PR inventory, no I/O and no Cursor calls."""
    if not isinstance(bundle, dict) or bundle.get("schema_version") != 1:
        return _reply("STOP", "invalid_bundle_schema")

    collector = bundle.get("collector")
    observed = bundle.get("observed")
    task = bundle.get("task")
    semantic = bundle.get("semantic")
    if not all(isinstance(v, dict) for v in (collector, observed, task, semantic)):
        return _reply("STOP", "missing_provenance_inputs")
    if (collector.get("status") != "OBSERVED"
            or collector.get("missing_capabilities") != []
            or collector.get("warnings") not in ([], None)):
        return _reply("STOP", "collector_partial_or_untrusted")

    facts = collector.get("observed_facts")
    if not isinstance(facts, dict):
        return _reply("STOP", "missing_collector_facts")
    for key in ("repo", "issue_number", "issue_state", "default_sha"):
        if facts.get(key) != observed.get(key):
            return _reply("STOP", "observed_github_source_mismatch")
    if (facts.get("repo") != task.get("repository")
            or facts.get("repo") != semantic.get("repository")
            or facts.get("issue_number") != semantic.get("issue_number")
            or semantic.get("issue_url") != task.get("issue")
            or facts.get("default_sha") != semantic.get("default_sha")
            or facts.get("issue_state") != semantic.get("issue_state")):
        return _reply("STOP", "cross_module_issue_or_sha_mismatch")

    # Source completeness belongs to a separately checked, task-local PR
    # inventory. A full issue-event page alone is NOT an exhaustive PR graph.
    if (observed.get("related_inventory_complete") is not True
            or semantic.get("inventory_complete") is not True
            or facts.get("linked_pr_inventory_truncated") is True
            or facts.get("related_prs_files_pagination_complete") is not True):
        return _reply("STOP", "relevant_pr_graph_not_complete")

    actual = facts.get("related_prs")
    reviewed = semantic.get("prs")
    verified = observed.get("related_prs")
    if not all(isinstance(x, list) for x in (actual, reviewed, verified)):
        return _reply("STOP", "incomplete_pr_mapping")

    def index(items: list[dict]) -> dict[int, dict] | None:
        out = {}
        for entry in items:
            if (not isinstance(entry, dict) or type(entry.get("number")) is not int
                    or entry["number"] <= 0 or entry["number"] in out):
                return None
            out[entry["number"]] = entry
        return out

    cprs, sprs, oprs = index(actual), index(reviewed), index(verified)
    if cprs is None or sprs is None or oprs is None or set(cprs) != set(sprs) or set(cprs) != set(oprs):
        return _reply("STOP", "missing_or_extra_related_pr")

    for num, p in sprs.items():
        observed_pr, from_collector = oprs[num], cprs[num]
        if (p.get("head_sha") != from_collector.get("head_sha")
                or p.get("head_sha") != observed_pr.get("head_sha")
                or p.get("state") != from_collector.get("state")
                or p.get("state") != observed_pr.get("state")
                or p.get("observed_head_sha") != from_collector.get("head_sha")):
            return _reply("STOP", "changed_or_conflicting_related_pr")
        # GitHub accepts state lower-case; semantic classifier also expects
        # lower-case. Parent/base changes between samples must be caught.
        if (p.get("base_sha") != from_collector.get("base_sha")
                or p.get("base_sha") != observed_pr.get("base_sha")
                or p.get("observed_base_sha") != from_collector.get("base_sha")):
            return _reply("STOP", "changed_pr_base_sha")
        if (sorted(p.get("changed_paths", [])) != sorted(from_collector.get(
                "changed_files_observed", []))
                or from_collector.get("changed_files_pagination_complete") is not True):
            return _reply("STOP", "changed_pr_paths_or_incomplete_files")

    # Reuse accepted consistency gates rather than reimplement acceptance logic.
    gate = reconcile({"task": task, "observed": observed})
    if gate.get("verification") != "CONSISTENT_ONLY":
        return _reply("STOP", "accepted_decision_evidence_inconsistent")
    outcome = gate.get("status")
    issue = task.get("issue")
    sha = observed.get("default_sha")

    if outcome in ("ALREADY_ACCEPTED", "SUPERSEDED"):
        return _reply("NO_READY_WORK", "accepted_or_superseded_not_new_work",
                      issue=issue, sha=sha)
    if outcome in ("UNSAFE", "NEEDS_EVIDENCE"):
        return _reply("STOP", "decision_gate_denied_or_incomplete", issue=issue, sha=sha)
    if outcome == "OWNER_GATE":
        return _reply("OWNER_GATE", "decision_owner_gate", issue=issue, sha=sha)
    if outcome in ("WAITING_DEPENDENCY", "EXTERNAL_BLOCKED"):
        return _reply("WAIT", "decision_dependency_or_external_block", issue=issue, sha=sha)
    if outcome not in ("EXISTING_PR", "READY"):
        return _reply("STOP", "unexpected_decision_gate_outcome")

    # The accepted Decision Gate returns EXISTING_PR before evaluating some
    # independent gates (owner/dependency/writer). Never treat that recommendation
    # as permission to bypass them in a composed orchestration preview.
    task_evidence = task.get("evidence", {})
    if (task_evidence.get("scope") == "owner_gated"
            or task_evidence.get("owner_gate") is True
            or task_evidence.get("owner_permission") != "granted"):
        return _reply("OWNER_GATE", "unresolved_task_owner_gate", issue=issue, sha=sha)
    if task_evidence.get("owner_gate") is not False:
        return _reply("STOP", "task_owner_gate_unknown", issue=issue, sha=sha)
    if task_evidence.get("writer") == "active":
        return _reply("WAIT", "task_writer_active", issue=issue, sha=sha)
    if task_evidence.get("writer") != "idle":
        return _reply("STOP", "task_writer_unknown", issue=issue, sha=sha)
    if task_evidence.get("external") == "blocked":
        return _reply("WAIT", "external_dependency_blocked", issue=issue, sha=sha)
    if task_evidence.get("external") != "clear":
        return _reply("STOP", "external_evidence_unknown", issue=issue, sha=sha)
    deps = task_evidence.get("dependencies")
    if not isinstance(deps, list) or any(
            not isinstance(x, dict) or x.get("state") not in ("accepted", "pending", "unknown")
            for x in deps):
        return _reply("STOP", "dependency_state_unknown", issue=issue, sha=sha)
    if any(x["state"] == "unknown" for x in deps):
        return _reply("STOP", "dependency_unverified", issue=issue, sha=sha)
    if any(x["state"] == "pending" for x in deps):
        return _reply("WAIT", "dependency_not_yet_accepted", issue=issue, sha=sha)

    semantic_result = reconcile_one(semantic)
    decision = semantic_result.get("action")
    if decision == "STOP":
        return _reply("STOP", "semantic_reconciliation_not_proven", issue=issue, sha=sha)
    if decision == "OWNER_GATE":
        return _reply("OWNER_GATE", "semantic_owner_gate", issue=issue, sha=sha)
    if decision == "WAIT_DEPENDENCY":
        return _reply("WAIT", "semantic_dependency_or_collision", issue=issue, sha=sha)
    if decision == "NO_READY_WORK":
        return _reply("STOP", "contradictory_accepted_semantics", issue=issue, sha=sha)
    if decision == "REUSE_EXISTING_PR" and outcome == "EXISTING_PR":
        selected = semantic_result.get("selected_pr")
        matches = [p for p in task["evidence"]["related_prs"]
                   if p.get("number") == selected and p.get("relation") == "same_outcome"]
        if len(matches) != 1:
            return _reply("STOP", "existing_pr_relation_conflict", issue=issue, sha=sha)
        return _reply("REUSE_EXISTING_PR", "review_existing_pr_before_new_code",
                      issue=issue, sha=sha, pr=selected)
    if decision == "READY_FOR_OWNER_DISPATCH" and outcome == "READY":
        return _reply("READY_FOR_OWNER_DISPATCH", "independent_owner_scoped_candidate_only",
                      issue=issue, sha=sha)
    return _reply("STOP", "cross_module_decision_conflict", issue=issue, sha=sha)
