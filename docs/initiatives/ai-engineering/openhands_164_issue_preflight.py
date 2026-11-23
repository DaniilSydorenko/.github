#!/usr/bin/env python3
"""Read-only Issue #216–#226 scope satisfaction checks (no model, no writes)."""
from __future__ import annotations

import pathlib

from openhands_164_patch_contract import ALLOWED


def _normalized(text: str) -> str:
    return " ".join(text.lower().split())


def early_readonly_satisfaction(workspace: str | pathlib.Path, issue: int = 216) -> dict | None:
    """Local file check only; no network, lease, secrets, or budget."""
    verdict = evaluate_issue_satisfaction(issue, workspace)
    if verdict.get("reason") != "ALREADY_SATISFIED":
        return None
    return {
        **verdict,
        "preflight_mode": "read_only_before_lease_and_budget",
        "lease_acquired": False,
        "provider_spend_attested": False,
        "publish_authorized": False,
        "next_action": "owner_go_for_issue_217_when_sequential_chain_authorized",
    }


def evaluate_issue_satisfaction(issue: int, workspace: str | pathlib.Path) -> dict:
    """Return ALREADY_SATISFIED when the allowed doc already meets pilot goals."""
    if type(issue) is not int or issue not in ALLOWED:
        return {"decision": "STOP", "reason": "unexpected_issue"}
    root = pathlib.Path(workspace)
    target = root / ALLOWED[issue]
    if not target.is_file() or target.is_symlink():
        return {"decision": "CONTINUE", "reason": "target_doc_absent"}
    content = target.read_text(encoding="utf-8")
    if not content.strip():
        return {"decision": "CONTINUE", "reason": "target_doc_empty"}
    text = _normalized(content)
    if issue == 216:
        required = (
            "node 22" in text and "node 24" in text and "supported" in text
            and "node 26" in text and "smoke" in text
            and ("minimum supported" in text or "minimum" in text and "supported" in text)
        )
        if required:
            return {
                "decision": "STOP",
                "reason": "ALREADY_SATISFIED",
                "issue": issue,
                "target": ALLOWED[issue],
                "model_invoked": False,
                "github_write": False,
            }
        return {"decision": "CONTINUE", "reason": "issue216_documentation_incomplete"}
    return {"decision": "CONTINUE", "reason": "satisfaction_check_not_defined_for_issue"}


def self_test() -> None:
    import tempfile

    satisfied = """# Runtime Compatibility

| Node 22 | Supported |
| Node 24 | Supported |
| Node 26 | Compatibility smoke |

The Node 26 row is a forward-compatibility smoke signal. It does not redefine the minimum supported Node.js version.
"""
    incomplete = "# TODO\n\nNode versions TBD.\n"
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        path = root / ALLOWED[216]
        path.parent.mkdir(parents=True)
        path.write_text(satisfied, encoding="utf-8")
        ok = evaluate_issue_satisfaction(216, root)
        assert ok["reason"] == "ALREADY_SATISFIED"
        path.write_text(incomplete, encoding="utf-8")
        assert evaluate_issue_satisfaction(216, root)["decision"] == "CONTINUE"
        assert evaluate_issue_satisfaction(217, root)["reason"] == "target_doc_absent"
    print("PASS: #164 issue satisfaction preflight (offline)")


if __name__ == "__main__":
    self_test()