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
        self.assertIn('actions/runs?per_page=30', text)
        self.assertIn('latest_bad_workflow_count', text)

    def test_health_workflow_changes_are_ci_guarded(self):
        text = CONTROL.read_text()
        path = '.github/workflows/reusable-autopilot-health.yml'
        self.assertGreaterEqual(
            text.count(path),
            2,
            "health workflow must be included in both PR and main-push GRS path filters",
        )


if __name__ == "__main__":
    unittest.main()
