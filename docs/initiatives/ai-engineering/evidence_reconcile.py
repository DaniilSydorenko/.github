"""Offline cross-check of a task decision against independently captured metadata.

Consistency checks only. Caller-provided data is NOT cryptographic proof of live
GitHub state, semantic PR equivalence, ownership or absence of other writers.
"""

import json
import re
import sys
from pathlib import Path

from decision_gate import decide

_SHA = re.compile(r"[0-9a-f]{40}\Z")
_URL = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)\Z")


def reconcile(envelope):
    def blocked(reason):
        return {"status": "NEEDS_EVIDENCE", "reason": reason,
                "next_action": "Re-fetch authoritative GitHub metadata; do not dispatch.",
                "launched": False, "verification": "FAILED"}

    if not isinstance(envelope, dict):
        return blocked("No observation envelope")
    task, observed = envelope.get("task"), envelope.get("observed")
    if not isinstance(task, dict) or not isinstance(observed, dict):
        return blocked("Task and independently read observations are required")
    e = task.get("evidence")
    if not isinstance(e, dict):
        return blocked("Task evidence is missing")
    repo = task.get("repository")
    issue_url = task.get("issue")
    match = _URL.fullmatch(issue_url) if isinstance(issue_url, str) else None
    if not match or repo != match.group(1):
        return blocked("Issue URL does not identify the target repository")
    if observed.get("repo") != repo:
        return blocked("Observation belongs to a different repository")
    if observed.get("issue_number") != int(match.group(2)):
        return blocked("Observed issue number differs")
    if observed.get("issue_state") != e.get("issue_state"):
        return blocked("Issue state changed after task snapshot")
    live = observed.get("default_sha")
    if not isinstance(live, str) or not _SHA.fullmatch(live):
        return blocked("Observed default branch SHA is missing or invalid")
    if live != e.get("default_sha") or live != e.get("checked_sha"):
        return blocked("Default branch advanced after task snapshot")
    if observed.get("related_inventory_complete") is not True or e.get("inventory_complete") is not True:
        return blocked("Relevant PR inventory is incomplete")
    observed_prs = observed.get("related_prs")
    declared_prs = e.get("related_prs")
    if not isinstance(observed_prs, list) or not isinstance(declared_prs, list):
        return blocked("PR inventory is not a list")
    by_num = {}
    for pr in observed_prs:
        if (not isinstance(pr, dict) or type(pr.get("number")) is not int
                or pr["number"] <= 0 or pr["number"] in by_num
                or not isinstance(pr.get("head_sha"), str)
                or not _SHA.fullmatch(pr["head_sha"])
                or pr.get("state") not in ("open", "closed")):
            return blocked("Duplicate, malformed or ambiguous observed PR")
        by_num[pr["number"]] = pr
    declared_numbers = set()
    for pr in declared_prs:
        if not isinstance(pr, dict) or type(pr.get("number")) is not int:
            return blocked("Malformed task PR reference")
        num = pr["number"]
        if num in declared_numbers or num not in by_num:
            return blocked("Task references duplicate or unobserved PR")
        declared_numbers.add(num)
        current = by_num[num]
        if current["state"] != "open" or pr.get("head_sha") != current["head_sha"]:
            return blocked("Related PR was merged/closed or changed HEAD")
    if declared_numbers != set(by_num):
        return blocked("Unclassified relevant PR present in independent inventory")
    accepted = observed.get("accepted_shas")
    if not isinstance(accepted, list) or any(not isinstance(sha, str) or not _SHA.fullmatch(sha) for sha in accepted):
        return blocked("Accepted-commit observation missing or malformed")
    accepted_set = set(accepted)
    commit = e.get("accepted_commit")
    if commit is not None and commit not in accepted_set:
        return blocked("Claimed accepted implementation commit is not observed on default branch")
    replacement = e.get("superseded_by")
    if isinstance(replacement, dict) and replacement.get("accepted_sha") not in accepted_set:
        return blocked("Superseding change is not observed on default branch")
    result = decide(task)
    result["verification"] = "CONSISTENT_ONLY"
    return result


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 evidence_reconcile.py <observed-task-envelope.json>", file=sys.stderr)
        return 2
    try:
        envelope = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "NEEDS_EVIDENCE", "reason": str(exc), "launched": False}))
        return 2
    result = reconcile(envelope)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "READY" else 1


if __name__ == "__main__":
    sys.exit(main())
