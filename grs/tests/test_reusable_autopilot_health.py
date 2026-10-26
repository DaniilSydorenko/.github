"""Regression tests for the shared, read-only GitHub Actions health signal.

Runs the actual inline Bash with a mock GH CLI; never calls GitHub or Cursor.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HEALTH = ROOT / ".github/workflows/reusable-autopilot-health.yml"
CONTROL = ROOT / ".github/workflows/grs-control-plane.yml"


def health_shell_script() -> str:
    text = HEALTH.read_text(encoding="utf-8")
    lines = text.split("        run: |\n", 1)[1].splitlines()
    return "\n".join(
        line[10:] if line.startswith("          ") else line for line in lines
    ) + "\n"


class ReusableAutopilotHealthContractTest(unittest.TestCase):
    def test_health_signal_stays_actions_only_and_fail_closed(self):
        text = HEALTH.read_text(encoding="utf-8")
        self.assertNotIn("statusCheckRollup", text)
        self.assertNotIn("gh pr list", text)
        self.assertNotIn("/pulls", text)
        self.assertNotIn("open_failing_pr_count", text)
        self.assertIn('actions/workflows?per_page=100', text)
        self.assertIn(
            'actions/workflows/$workflow_id/runs?branch=$default_branch&status=completed&per_page=1',
            text,
        )
        self.assertNotIn("actions/runs?branch=$default_branch&per_page=100", text)
        self.assertIn("incomplete or malformed workflow inventory", text)
        self.assertIn('default_branch="$(gh api', text)
        self.assertIn('latest_bad_workflow_count', text)

    def test_pr_origin_does_not_consume_reusable_runner(self):
        text = HEALTH.read_text(encoding="utf-8")
        self.assertIn("github.event_name != 'workflow_run'", text)
        self.assertIn(
            "github.event.workflow_run.head_branch == github.event.repository.default_branch",
            text,
        )
        self.assertIn("  workflow_call:", text)
        self.assertIn("  actions: read", text)
        self.assertIn("  contents: read", text)
        self.assertNotIn("contents: write", text)

    def test_hq_help_ignores_pr_completions_but_keeps_main_and_schedule(self):
        help_text = (ROOT / ".github/workflows/autopilot-help.yml").read_text()
        self.assertIn("  workflow_run:", help_text)
        trigger = help_text.split("  workflow_run:", 1)[1].split("  schedule:", 1)[0]
        self.assertIn('      - "GRS Control Plane"', trigger)
        self.assertIn("    branches: [main]", trigger)
        self.assertIn("    types: [completed]", trigger)
        self.assertIn('    - cron: "41 */3 * * *"', help_text)
        self.assertIn("  workflow_dispatch:", help_text)
        self.assertIn("reusable-autopilot-health.yml@main", help_text)

    def test_health_workflow_changes_are_ci_guarded(self):
        text = CONTROL.read_text(encoding="utf-8")
        for path in (
            ".github/workflows/reusable-autopilot-health.yml",
            ".github/workflows/autopilot-help.yml",
        ):
            self.assertGreaterEqual(
                text.count(path), 2,
                f"{path} must be included in PR and main-push GRS path filters",
            )


@unittest.skipUnless(shutil.which("jq"), "GitHub ubuntu-latest has jq")
class HealthSignalMockedBashTests(unittest.TestCase):
    """Mock all GH endpoints; exercise the real reusable shell, not copied logic."""

    def run_health(self, *, conclusion="success", runs_present=True,
                   incomplete=False, wrong_branch=False, omit_endpoint=False):
        repo = "test-owner/test-repo"
        workflows = [
            {"id": 101, "name": "CI", "state": "active"},
            {"id": 202, "name": "Autopilot Help Signal", "state": "active"},
            {"id": 303, "name": "Unused disabled", "state": "disabled_manually"},
        ]
        endpoint = (
            f"repos/{repo}/actions/workflows/101/runs?"
            "branch=main&status=completed&per_page=1"
        )
        fixtures = {
            f"repos/{repo}": {"default_branch": "main"},
            f"repos/{repo}/actions/workflows?per_page=100": {
                "total_count": 101 if incomplete else len(workflows),
                "workflows": workflows,
            },
        }
        if not omit_endpoint:
            fixtures[endpoint] = {"workflow_runs": (
                [{"head_branch": "PR-branch" if wrong_branch else "main",
                  "conclusion": conclusion}]
                if runs_present else []
            )}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            f = root / "mock.json"
            f.write_text(json.dumps(fixtures), encoding="utf-8")
            gh = root / "gh"
            gh.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "with open(os.environ['GH_MOCK_DATA'], encoding='utf-8') as fh:\n"
                "    data = json.load(fh)\n"
                "key = sys.argv[2]\n"
                "if key not in data:\n"
                "    print('unmocked GitHub endpoint: ' + key, file=sys.stderr)\n"
                "    sys.exit(2)\n"
                "print(json.dumps(data[key]))\n",
                encoding="utf-8",
            )
            gh.chmod(0o755)
            summary = root / "summary.txt"
            env = dict(os.environ)
            env.update({
                "PATH": str(root) + os.pathsep + os.environ.get("PATH", ""),
                "GH_MOCK_DATA": str(f),
                "GITHUB_REPOSITORY": repo,
                "GITHUB_STEP_SUMMARY": str(summary),
                "GH_TOKEN": "synthetic-no-network",
            })
            result = subprocess.run(
                ["bash", "-c", health_shell_script()],
                capture_output=True, text=True, env=env, check=False,
                timeout=12,
            )
            return result, summary.read_text() if summary.exists() else ""

    def test_latest_failed_ci_detected_even_if_global_100_run_sample_would_miss_it(self):
        result, summary = self.run_health(conclusion="failure")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("AUTOPILOT HELP REQUEST", summary)
        self.assertIn("latest_bad_workflow_count=1", summary)
        self.assertIn("checked_active_workflow_count=1", summary)

    def test_latest_completed_success_is_clear(self):
        result, summary = self.run_health(conclusion="success")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Repository health signal is clear", summary)

    def test_no_completed_run_is_not_an_unrelated_failure(self):
        result, summary = self.run_health(runs_present=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("checked_active_workflow_count=1", summary)

    def test_incomplete_workflow_inventory_fails_closed(self):
        result, summary = self.run_health(incomplete=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("incomplete or malformed workflow inventory", result.stderr)
        self.assertNotIn("Repository health signal is clear", summary)

    def test_wrong_branch_response_fails_closed(self):
        result, summary = self.run_health(wrong_branch=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UNKNOWN", result.stderr)
        self.assertNotIn("Repository health signal is clear", summary)

    def test_unknown_conclusion_fails_closed(self):
        result, summary = self.run_health(conclusion=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UNKNOWN", result.stderr)
        self.assertNotIn("Repository health signal is clear", summary)

    def test_api_error_does_not_claim_health(self):
        result, summary = self.run_health(omit_endpoint=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unmocked GitHub endpoint", result.stderr)
        self.assertNotIn("Repository health signal is clear", summary)


if __name__ == "__main__":
    unittest.main()
