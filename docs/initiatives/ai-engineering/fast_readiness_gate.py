#!/usr/bin/env python3
"""Fast, zero-network, zero-model change gate for AI-ENG #164.

PASS means only local source/contract checks passed. NEVER live readiness.
"""
from __future__ import annotations
import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TESTS = [
    ["openhands_live_orchestrator.py", "--self-test"],
    ["openhands_three_issue_gate.py"],
    ["test_openhands_164_singleton.py"],
    ["openhands_164_lease_preconditions.py"],
    ["test_github_ref_lease.py"],
    ["test_run9_rejected_release.py"],
]


def static_contract(files: dict[str, str]) -> list[str]:
    problems = []
    workflow = files.get("workflow", "")
    orchestrator = files.get("orchestrator", "")
    for marker in ("offline-contract:", "test_openhands_164_singleton.py",
                   "openhands_live_orchestrator.py", "cancel-in-progress: false"):
        if marker not in workflow:
            problems.append("workflow_missing:" + marker)
    if 'environment: ai-eng-lease-owner' not in workflow:
        problems.append("protected_environment_missing")
    if 'live_authorization_not_integrated' not in orchestrator:
        problems.append("read_only_stop_marker_missing")
    for forbidden in ("subprocess.run(", "subprocess.Popen(", "os.system("):
        if forbidden in orchestrator:
            problems.append("unexpected_process_launch:" + forbidden)
    return problems


def live_integration_observations(files: dict[str, str]) -> list[str]:
    """Static triage of known launch paths; never an authorization decision.

    Parse the runner's actual calls rather than trusting a marker string in
    comments. This is intentionally conservative: a missing signal is NOT
    proof of global singleton enforcement or credential isolation.
    """
    runner = files.get("runner", "")
    orchestrator = files.get("orchestrator", "")
    blockers = []
    try:
        tree = ast.parse(runner)
    except SyntaxError:
        return ["legacy_runner_unparseable"]
    calls = {node.func.id for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    if "execute_authorized" in calls:
        blockers.append("legacy_runner_model_call_requires_trusted_lease_integration_review")
    if "live_authorization_not_integrated" in orchestrator:
        blockers.append("three_issue_orchestrator_read_only")
    return blockers


def governance_contract(files: dict[str, str]) -> list[str]:
    problems = []
    for key, markers in {
        'agents': ('DELIVERY_GOVERNANCE.md', 'DELIVERY_PLAN_164.md'),
        'governance': ('New chat bootstrap', 'Cross-repository adoption', 'Owner-time budget'),
        'plan': ('Critical path', 'Minimum evidence', 'Deferred'),
        'adoption': ('AGENTS.md', 'NOT_INVENTORIED', 'ENFORCED'),
    }.items():
        if not files.get(key):
            problems.append('governance_missing_file:' + key)
        for marker in markers:
            if marker not in files.get(key, ''):
                problems.append('governance_missing_marker:' + key + ':' + marker)
    return problems


def self_test() -> None:
    base = {"workflow": """offline-contract:
test_openhands_164_singleton.py
openhands_live_orchestrator.py
cancel-in-progress: false
environment: ai-eng-lease-owner""",
            "orchestrator": "live_authorization_not_integrated"}
    assert static_contract(base) == []
    for field, marker in (("workflow", "test_openhands_164_singleton.py"),
                          ("workflow", "environment: ai-eng-lease-owner"),
                          ("orchestrator", "live_authorization_not_integrated")):
        bad = dict(base)
        bad[field] = bad[field].replace(marker, "")
        assert static_contract(bad), marker
    bad = dict(base)
    bad["orchestrator"] += "\nsubprocess.Popen("
    assert static_contract(bad)
    assert live_integration_observations({"runner": "execute_authorized(root, key)", "orchestrator": "live_authorization_not_integrated"}) == ["legacy_runner_model_call_requires_trusted_lease_integration_review", "three_issue_orchestrator_read_only"]
    assert live_integration_observations({"runner": "# execute_authorized(root, key)", "orchestrator": ""}) == []
    assert live_integration_observations({"runner": "def broken(", "orchestrator": ""}) == ["legacy_runner_unparseable"]
    assert live_integration_observations({"runner": "", "orchestrator": ""}) == []
    fixture = {"agents": "DELIVERY_GOVERNANCE.md DELIVERY_PLAN_164.md", "governance": "New chat bootstrap Cross-repository adoption Owner-time budget", "plan": "Critical path Minimum evidence Deferred", "adoption": "AGENTS.md NOT_INVENTORIED ENFORCED"}
    assert governance_contract(fixture) == []
    assert governance_contract({**fixture, "agents": ""})
    print("PASS: fast-gate negative fixtures (not live admission)")


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return 0
    if sys.argv[1:]:
        print("Usage: fast_readiness_gate.py [--self-test]", file=sys.stderr)
        return 2
    workflow = ROOT / ".github/workflows/ai-eng-openhands-readiness.yml"
    orchestrator = HERE / "openhands_live_orchestrator.py"
    problems = static_contract({"workflow": workflow.read_text(),
                                "orchestrator": orchestrator.read_text()})
    problems.extend(governance_contract({
        "agents": (ROOT / "AGENTS.md").read_text(),
        "governance": (HERE / "DELIVERY_GOVERNANCE.md").read_text(),
        "plan": (HERE / "DELIVERY_PLAN_164.md").read_text(),
        "adoption": (HERE / "REPOSITORY_ADOPTION_KIT.md").read_text(),
    }))
    for source in (HERE / "openhands_live_orchestrator.py", HERE / "openhands_164_lease_preconditions.py", HERE / "openhands_three_issue_gate.py"):
        try:
            ast.parse(source.read_text(), filename=str(source))
        except SyntaxError:
            problems.append("python_syntax_invalid:" + source.name)
    runner = HERE / "openhands_live_runner.py"
    integration_blockers = live_integration_observations({
        "runner": runner.read_text(), "orchestrator": orchestrator.read_text()})
    results = []
    for command in TESTS:
        cmd = [sys.executable, str(HERE / command[0]), *command[1:]]
        try:
            p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, timeout=30)
            results.append({"test": command[0], "pass": p.returncode == 0,
                            "detail": (p.stderr or p.stdout)[-600:]})
        except (OSError, subprocess.TimeoutExpired) as exc:
            results.append({"test": command[0], "pass": False,
                            "detail": type(exc).__name__})
    if any(not x["pass"] for x in results):
        problems.append("offline_contract_failure")
    report = {"gate": "G0_G1_ONLY", "status": "PASS" if not problems else "FAIL",
              "live_admission": "BLOCKED", "g2": "BLOCKED", "g3": "UNKNOWN",
              "g4": "BLOCKED", "integration_observations": integration_blockers,
              "problems": problems, "tests": results,
              "model_calls": 0, "github_writes": 0}
    print(json.dumps(report, sort_keys=True))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
