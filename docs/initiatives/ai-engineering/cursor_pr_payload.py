"""Build (NEVER POST) a bounded Cursor Cloud Agent v1 existing-PR request.

This is offline contract construction, not evidence of owner approval, budget
enforcement, an acquired lease, account-wide exclusivity or an actual run.
Only a future authenticated gate may submit the payload after live checks.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from github_ref_lease import agent_id_for

SHA = re.compile(r"[0-9a-f]{40}\Z")
SLUG = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?/[A-Za-z0-9_.-]+\Z")
MODEL = re.compile(r"[A-Za-z0-9_.:/+-]{2,80}\Z")


class PayloadError(ValueError):
    pass


def existing_pr_payload(*, request_id: str, repository: str,
                        pr_number: int, exact_pr_head: str, issue_number: int,
                        model_id: str, model_allowlist: frozenset[str]) -> dict:
    """Offline preview. Return a payload within a non-launchable envelope.

    Revalidate every field against live GitHub/provider just BEFORE launch.
    Invalid/replayed request IDs are rejected by the *separate* durable lease.
    """
    agent_id = agent_id_for(request_id)  # Cursor v1 supports idempotent agentId
    if (not isinstance(repository, str) or not SLUG.fullmatch(repository)
            or repository.split("/", 1)[1] in (".", "..")):
        raise PayloadError("invalid repository")
    if type(pr_number) is not int or pr_number <= 0:
        raise PayloadError("invalid PR number")
    if type(issue_number) is not int or issue_number <= 0:
        raise PayloadError("invalid authorized Issue number")
    if not isinstance(exact_pr_head, str) or not SHA.fullmatch(exact_pr_head):
        raise PayloadError("invalid PR HEAD SHA")
    if (not isinstance(model_id, str) or not MODEL.fullmatch(model_id)
            or not isinstance(model_allowlist, frozenset)
            or model_id not in model_allowlist):
        raise PayloadError("model not explicitly allowlisted")

    repo_url = f"https://github.com/{repository}"
    pr_url = f"{repo_url}/pull/{pr_number}"
    bounded = (
        f"Work ONLY on existing GitHub PR #{pr_number} ({pr_url}) "
        f"for authorized Issue #{issue_number}. "
        f"Re-read the live PR HEAD; expected {exact_pr_head}. "
        "If it changed, or another writer is active: STOP and report. "
        "Integration Before Implementation: complete THIS PR's specific "
        "existing change, review/fix bounded defects, run focused and "
        "mandatory exact-head CI. Do not create an unrelated feature, "
        "new branch, replacement PR, subagent, or second task. "
        "NEVER merge, deploy, release, change secrets/billing/permissions, "
        "publish private information, or bypass owner/security gates. "
        "Attempt no more than two evidence-backed corrections. "
        "Report exact committed HEAD, tests, CI links and blockers. "
        "A prompt is not a technical security boundary."
    )
    return {
        "status": "PROPOSAL_ONLY",
        "launch_allowed": False,
        "payload": {
            "agentId": agent_id,
            "prompt": {"text": bounded},
            "model": {"id": model_id},
            "repos": [{"url": repo_url, "prUrl": pr_url}],
            "workOnCurrentBranch": True,
            "autoCreatePR": False,
            "mode": "agent",
        },
        "required_outside_this_function": [
            "fresh_authenticated_github_sha_and_semantics",
            "atomic_acquired_global_lease",
            "fresh_global_cursor_agent_inventory",
            "verified_cursor_and_external_billing_safety",
            "authenticated_owner_scope_and_domain_permission",
            "single_transaction_controller_and_protected_launch_routes",
        ],
    }
