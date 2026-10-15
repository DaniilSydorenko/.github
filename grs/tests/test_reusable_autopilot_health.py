from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
HEALTH = ROOT / ".github" / "workflows" / "reusable-autopilot-health.yml"
CONTROL = ROOT / ".github" / "workflows" / "grs-control-plane.yml"


class ReusableAutopilotHealthContractTest(unittest.TestCase):
    def test_health_signal_stays_actions_only(self):
        text = HEALTH.read_text()
        self.assertNotIn("statusCheckRollup", text)
        self.assertNotIn("gh pr list", text)
        self.assertNotIn("/pulls", text)
        self.assertNotIn("open_failing_pr_count", text)
        self.assertIn('actions/runs?branch=$default_branch&per_page=100', text)
        self.assertNotIn('actions/runs?per_page=100', text)
        self.assertIn('repos/$GITHUB_REPOSITORY" --jq \'.default_branch\'', text)
        self.assertIn('--arg default_branch "$default_branch"', text)
        self.assertIn('select(.head_branch == $default_branch)', text)
        self.assertNotIn('select(.head_branch == "main")', text)
        self.assertIn('group_by(.workflow_id)', text)
        self.assertIn('actions/workflows?per_page=100', text)
        self.assertIn('select(.state == "active")', text)
        self.assertIn('map(sort_by(.created_at) | reverse | .[0])', text)
        self.assertIn('latest_bad_workflow_count', text)
        self.assertNotIn('| .[0:1]', text)

    def test_recent_runs_query_is_filtered_before_github_pagination(self):
        # Default branch runs must not be evicted by a burst of PR runs
        # before the existing jq health/group-by rules inspect the payload.
        text = HEALTH.read_text()
        default_knowledge = text.index('default_branch="$(gh api')
        scoped_query = text.index('actions/runs?branch=$default_branch&per_page=100')
        self.assertLess(default_knowledge, scoped_query)
        self.assertIn('select(.head_branch == $default_branch)', text)
        self.assertNotIn('actions/runs?per_page=100', text)
        self.assertIn('group_by(.workflow_id)', text)
        self.assertIn('latest_bad_workflow_count', text)

    def test_hq_help_ignores_pr_completions_but_keeps_main_and_schedule(self):
        # Reusable health checks only default-branch workflows. A GRS PR
        # completion cannot alter that health result and must not launch
        # a redundant Help Signal workflow.
        help_text = (ROOT / ".github" / "workflows" / "autopilot-help.yml").read_text()
        self.assertIn("  workflow_run:", help_text)
        trigger = help_text.split("  workflow_run:", 1)[1].split("  schedule:", 1)[0]
        self.assertIn('      - "GRS Control Plane"', trigger)
        self.assertIn("    branches: [main]", trigger)
        self.assertIn("    types: [completed]", trigger)
        self.assertIn('    - cron: "41 */3 * * *"', help_text)
        self.assertIn("  workflow_dispatch:", help_text)
        self.assertIn("reusable-autopilot-health.yml@main", help_text)

    def test_health_workflow_changes_are_ci_guarded(self):
        text = CONTROL.read_text()
        for path in (
            '.github/workflows/reusable-autopilot-health.yml',
            '.github/workflows/autopilot-help.yml',
        ):
            self.assertGreaterEqual(
                text.count(path),
                2,
                f"{path} must be included in both PR and main-push GRS path filters",
            )


if __name__ == "__main__":
    unittest.main()
