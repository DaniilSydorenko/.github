from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
HEALTH = ROOT / ".github" / "workflows" / "reusable-autopilot-health.yml"
CONTROL = ROOT / ".github" / "workflows" / "grs-control-plane.yml"


class ReusableAutopilotHealthContractTest(unittest.TestCase):
    def test_pr_query_fails_closed(self):
        text = HEALTH.read_text()
        self.assertNotIn("|| echo '[]'", text)
        self.assertIn('if ! prs_json="$(gh pr list', text)
        self.assertIn("open_pr_query=FAILED", text)
        self.assertIn("refusing a false-clear signal", text)
        self.assertIn("exit 1", text)

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
