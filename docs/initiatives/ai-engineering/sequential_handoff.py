"""One-step sequential Issue handoff PREVIEW after an accepted PR integration.

No network, persistence, GitHub writes, provider call, scheduler or merge.
An input bundle is NOT trusted GitHub/owner proof; authenticated observation
must re-fetch facts immediately before any future execution. Specifically,
READY_FOR_OWNER_DISPATCH never means READY_TO_LAUNCH_CURSOR.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

_SHA = re.compile(r"[0-9a-f]{40}\Z")
_REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_MAX_ISSUES = 25
_MAX_PRS = 20


def _is_sha(x: Any) -> bool:
    return isinstance(x, str) and _SHA.fullmatch(x) is not None


def _positive(x: Any) -> bool:
    return type(x) is int and x > 0


def _paths(x: Any) -> bool:
    return (isinstance(x, list) and 0 < len(x) <= 40
            and all(isinstance(p, str) and p and not p.startswith("/")
                    and "\\" not in p and not any(s in (".", "..")
                    for s in p.split("/")) for p in x)
            and len(x) == len(set(x)))


def _out(action: str, reason: str, issue: int | None = None,
         request_id: str | None = None, pr: int | None = None) -> dict[str, Any]:
    return {
        "action": action, "reason": reason, "next_issue_number": issue,
        "existing_pr_number": pr, "proposed_request_id": request_id,
        "advisory_only": True, "provider_called": False,
        "cursor_launched": False, "cursor_launch_authorized": False,
        "git_write": False, "merge_authorized": False,
        "owner_approval_bypassed": False,
    }


def preview_next_after_merge(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Fail-closed one-step projection: validated prior merge -> one next Issue.

    Designed for reuse AFTER trusted GitHub collection and owner attestations,
    not to replace either. No automatic chaining or authorization is granted.
    """
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1:
        return _out("STOP", "unknown_schema")
    repo = snapshot.get("repository")
    if not isinstance(repo, str) or not _REPO.fullmatch(repo) or repo.count(".."):
        return _out("STOP", "invalid_repository")
    main = snapshot.get("main")
    if (not isinstance(main, dict) or not _is_sha(main.get("before_sha"))
            or not _is_sha(main.get("after_sha"))
            or main["before_sha"] != main["after_sha"]):
        return _out("STOP", "main_head_unverified_or_moved")
    if (snapshot.get("relevant_inventory_complete") is not True
            or snapshot.get("owner_authority_verified") is not True):
        return _out("STOP", "inventory_or_owner_authority_unverified")

    previous = snapshot.get("previous")
    if not isinstance(previous, dict) or not _positive(previous.get("pr_number")):
        return _out("STOP", "previous_pr_not_identified")
    if (previous.get("state") != "closed" or previous.get("merged") is not True
            or not _is_sha(previous.get("head_sha"))
            or not _is_sha(previous.get("merge_sha"))
            or previous.get("merge_on_default_verified") is not True):
        return _out("STOP", "previous_pr_not_proven_integrated")
    if (previous.get("ci") != "SUCCESS"
            or previous.get("secret_scan") != "SUCCESS"
            or previous.get("owner_merge_permission") != "granted"):
        return _out("STOP", "previous_ci_security_or_merge_authority_missing")
    if previous.get("owner_visual_acceptance") == "pending":
        return _out("OWNER_GATE", "previous_visual_acceptance_pending")
    if previous.get("owner_visual_acceptance") != "accepted":
        return _out("STOP", "previous_visual_acceptance_unverified")
    if previous.get("deployment") == "pending":
        return _out("WAIT", "previous_deployment_pending")
    if previous.get("deployment") not in ("accepted", "not_required"):
        return _out("STOP", "previous_deployment_unverified")

    writer = snapshot.get("writer")
    if not isinstance(writer, dict) or writer.get("inventory_complete") is not True:
        return _out("STOP", "writer_inventory_incomplete")
    if writer.get("status") == "active":
        return _out("WAIT", "domain_writer_busy")
    if writer.get("status") != "idle":
        return _out("STOP", "domain_writer_unknown")
    prs = writer.get("open_prs")
    if not isinstance(prs, list) or len(prs) > _MAX_PRS:
        return _out("STOP", "open_pr_inventory_unbounded")
    pr_index: dict[int, dict[str, Any]] = {}
    for item in prs:
        if not isinstance(item, dict) or not _positive(item.get("number")):
            return _out("STOP", "invalid_open_pr_entry")
        number = item["number"]
        if (number in pr_index or not _is_sha(item.get("head_sha"))
                or not _positive(item.get("issue_number"))
                or item.get("state") != "open"
                or item.get("files_complete") is not True
                or not _paths(item.get("changed_paths"))):
            return _out("STOP", "unverified_or_duplicate_open_pr")
        pr_index[number] = item

    queue = snapshot.get("queue")
    if not isinstance(queue, list) or len(queue) > _MAX_ISSUES:
        return _out("STOP", "queue_unbounded_or_unknown")
    orders: set[int] = set()
    issues: set[int] = set()
    for t in queue:
        if not isinstance(t, dict):
            return _out("STOP", "invalid_issue_entry")
        n, order = t.get("number"), t.get("order")
        if (not _positive(n) or not _positive(order)
                or n in issues or order in orders):
            return _out("STOP", "issue_identity_or_order_duplicate")
        issues.add(n)
        orders.add(order)
        if (t.get("state") not in ("open", "closed")
                or type(t.get("accepted")) is not bool
                or type(t.get("owner_approved")) is not bool
                or type(t.get("owner_gate")) is not bool
                or t.get("scope") not in ("ui_low_risk", "ui_owner_gated")
                or not _paths(t.get("allowed_paths"))
                or not isinstance(t.get("dependencies"), list)):
            return _out("STOP", "issue_authority_or_scope_unknown")
        deps = t["dependencies"]
        if (len(deps) > _MAX_ISSUES or any(
                not isinstance(d, dict) or not _positive(d.get("number"))
                or d.get("status") not in ("accepted", "pending", "unknown")
                for d in deps)
                or len(set(d["number"] for d in deps)) != len(deps)):
            return _out("STOP", "dependency_evidence_invalid")
        if (t["state"] == "closed" and not t["accepted"]):
            return _out("STOP", "closed_issue_not_accepted")
        if t["state"] == "open" and t["accepted"]:
            return _out("STOP", "contradictory_accepted_issue")

    if orders != set(range(1, len(queue) + 1)):
        return _out("STOP", "queue_order_not_contiguous")
    for task in sorted(queue, key=lambda t: t["order"]):
        if task["accepted"]:
            continue
        n = task["number"]
        if any(d["status"] == "unknown" for d in task["dependencies"]):
            return _out("STOP", "dependency_unknown", issue=n)
        if any(d["status"] == "pending" for d in task["dependencies"]):
            return _out("WAIT", "dependency_pending", issue=n)
        if task["owner_gate"] or not task["owner_approved"]:
            return _out("OWNER_GATE", "next_issue_requires_owner", issue=n)
        # Any existing PR is integration work before fresh implementation.
        related = [p for p in prs if p["issue_number"] == n]
        if len(related) > 1:
            return _out("STOP", "multiple_prs_for_next_issue", issue=n)
        if len(prs) > len(related):
            return _out("WAIT", "other_open_pr_requires_reconciliation", issue=n)
        if related:
            return _out("REUSE_EXISTING_PR", "integrate_before_implementation",
                        issue=n, pr=related[0]["number"])
        if task["scope"] != "ui_low_risk":
            return _out("OWNER_GATE", "product_ui_scope_not_autonomously_delegated", issue=n)

        # Stable ACROSS scheduler ticks and changing default HEADs. Not a launch
        # permit: authenticated billing, lease and domain ownership still apply.
        digest = hashlib.sha256(f"ai-eng-next-v1:{repo}:issue:{n}".encode()).hexdigest()
        return _out("READY_FOR_OWNER_DISPATCH", "preapproved_single_leaf_proposal_only",
                    issue=n, request_id="seq-" + digest[:32])
    if prs:
        return _out("WAIT", "open_prs_remain_after_queue_acceptance")
    return _out("NO_READY_WORK", "all_approved_queue_items_accepted")
