#!/usr/bin/env python3
"""Advisory, offline task-readiness evaluator for one owner-authorized GitHub task.

No network, GitHub writes, agent execution or mutable storage. Input is an
attested evidence snapshot: the caller must obtain and verify live sources.
"""

import json
import re
import sys
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
OUTCOMES = {
    "UNSAFE": "STOP: the requested task/scope is forbidden; return to the owning authority.",
    "NEEDS_EVIDENCE": "Re-read the exact owner issue, default branch and relevant PR/dependency evidence; do not dispatch.",
    "ALREADY_ACCEPTED": "Reconcile the existing owning issue/roadmap with accepted proof; do not implement twice.",
    "EXISTING_PR": "Review/reconcile the existing PR with its owning author; do not create a parallel writer.",
    "WAITING_DEPENDENCY": "Record the precise dependency/collision in its existing issue; choose independent authorized work elsewhere.",
    "OWNER_GATE": "Request the narrow missing owner decision; no agent dispatch or consequential mutation.",
    "EXTERNAL_BLOCKED": "Record the external requirement and resume only on new provider/owner evidence; do not retry blindly.",
    "READY": "Eligible for a *separate* approved execution invocation; recheck exact HEAD and ownership immediately before launch.",
}


def decide(s):
    """Return an advisory verdict. Missing or inconsistent evidence fails closed."""
    def answer(status, reason):
        return {"status": status, "reason": reason, "next_action": OUTCOMES[status],
                "launched": False}

    if not isinstance(s, dict) or s.get("schema_version") != 1:
        return answer("NEEDS_EVIDENCE", "Unknown or missing evidence schema")
    repo, issue, e = s.get("repository"), s.get("issue"), s.get("evidence")
    if (not isinstance(repo, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)
            or not isinstance(issue, str) or not issue.startswith(f"https://github.com/{repo}/issues/")
            or not isinstance(e, dict)):
        return answer("NEEDS_EVIDENCE", "Missing owner-bound repository, issue or evidence envelope")
    if e.get("scope") == "forbidden":
        return answer("UNSAFE", "Explicitly forbidden scope (including learner-owned work)")
    required = ("default_sha", "checked_sha", "inventory_complete", "issue_state",
                "accepted_commit", "accepted_proof", "related_prs", "dependencies",
                "writer", "scope", "owner_permission", "owner_gate", "external")
    if any(k not in e for k in required):
        return answer("NEEDS_EVIDENCE", "One or more mandatory observation fields absent")
    current, checked = e["default_sha"], e["checked_sha"]
    if (not isinstance(current, str) or not SHA.fullmatch(current)
            or current != checked or e["inventory_complete"] is not True):
        return answer("NEEDS_EVIDENCE", "Stale default HEAD or incomplete relevant PR inventory")
    if e["issue_state"] not in ("open", "closed"):
        return answer("NEEDS_EVIDENCE", "Unknown issue state")
    if not isinstance(e["related_prs"], list) or not isinstance(e["dependencies"], list):
        return answer("NEEDS_EVIDENCE", "Related PRs/dependencies not reliably enumerated")
    if e["accepted_commit"] is not None:
        if (isinstance(e["accepted_commit"], str) and SHA.fullmatch(e["accepted_commit"])
                and isinstance(e["accepted_proof"], str)
                and e["accepted_proof"].startswith(f"https://github.com/{repo}/")):
            return answer("ALREADY_ACCEPTED", "Outcome confirmed in accepted branch with source-linked proof")
        return answer("NEEDS_EVIDENCE", "Accepted claim lacks an immutable SHA and source proof")
    if e["accepted_proof"] is not None:
        return answer("NEEDS_EVIDENCE", "Proof provided without accepted commit")
    for p in e["related_prs"]:
        if (not isinstance(p, dict) or p.get("relation") not in
                ("same_outcome", "overlapping_paths", "stack_dependency", "unrelated")
                or not isinstance(p.get("number"), int) or p["number"] <= 0
                or not isinstance(p.get("head_sha"), str)
                or not SHA.fullmatch(p["head_sha"])):
            return answer("NEEDS_EVIDENCE", "Unknown relation or incomplete PR identity")
    matches = [p for p in e["related_prs"] if p["relation"] == "same_outcome"]
    if matches:
        return answer("EXISTING_PR", "Existing open PR(s) for same outcome: " + ", ".join("#" + str(p["number"]) for p in matches))
    collisions = [p for p in e["related_prs"] if p["relation"] in ("overlapping_paths", "stack_dependency")]
    if collisions:
        return answer("WAITING_DEPENDENCY", "Active path/stack dependency: " + ", ".join("#" + str(p["number"]) for p in collisions))
    for d in e["dependencies"]:
        if not isinstance(d, dict) or not isinstance(d.get("ref"), str) or d.get("state") not in ("accepted", "pending", "unknown"):
            return answer("NEEDS_EVIDENCE", "Unknown dependency state or reference")
    if any(d["state"] == "unknown" for d in e["dependencies"]):
        return answer("NEEDS_EVIDENCE", "Dependency acceptance not established")
    if any(d["state"] == "pending" for d in e["dependencies"]):
        return answer("WAITING_DEPENDENCY", "An owning prerequisite is not accepted")
    if e["scope"] not in ("allowed", "owner_gated"):
        return answer("NEEDS_EVIDENCE", "Task scope classification not confirmed")
    if e["scope"] == "owner_gated" or e["owner_gate"] is True:
        return answer("OWNER_GATE", "Owner-controlled operation or decision remains open")
    if e["external"] == "blocked":
        return answer("EXTERNAL_BLOCKED", "External provider/runtime evidence or access missing")
    if e["external"] != "clear":
        return answer("NEEDS_EVIDENCE", "External dependency cannot be classified")
    if e["issue_state"] != "open":
        return answer("NEEDS_EVIDENCE", "Closed issue does not itself prove accepted implementation")
    if e["writer"] == "active":
        return answer("WAITING_DEPENDENCY", "Existing active writer owns the branch/PR")
    if e["writer"] != "idle":
        return answer("NEEDS_EVIDENCE", "Cannot verify exclusive writer state")
    if e["owner_permission"] != "granted":
        return answer("OWNER_GATE", "Per-task owner authorization absent/unknown")
    if e["owner_gate"] is not False:
        return answer("NEEDS_EVIDENCE", "Owner-gate proof unknown")
    return answer("READY", "Bounded task has current evidence and no known collision/gate; invocation remains separate")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 decision_gate.py <attested-task-snapshot.json>", file=sys.stderr)
        return 2
    try:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "NEEDS_EVIDENCE", "error": str(exc), "launched": False}))
        return 2
    result = decide(data)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "READY" else 1


if __name__ == "__main__":
    sys.exit(main())
