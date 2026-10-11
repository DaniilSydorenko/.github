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
        self.assertIn('actions/runs?per_page=100', text)
        self.assertIn('select(.head_branch == "main")', text)
        self.assertIn('group_by(.name)', text)
        self.assertIn('map(sort_by(.created_at) | reverse | .[0])', text)
        self.assertIn('latest_bad_workflow_count', text)
        self.assertNotIn('| .[0:1]', text)

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

    def test_public_readme_changes_are_ci_guarded(self):
        text = CONTROL.read_text()
        self.assertEqual(
            text.count('      - "README.md"'),
            2,
            "README.md must trigger GRS on both PRs and main pushes",
        )


if __name__ == "__main__":
    unittest.main()
