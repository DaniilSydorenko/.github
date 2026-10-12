"""Regression checks for the HQ engineering round protocol.

These tests verify document integrity only. They do not approve Governance v1,
enforce policy in domain repositories, or prove a live end-to-end pilot.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "reports/github-hq/ENGINEERING-ROUND-PROTOCOL.md"
STAGES = (
    "DISCOVERY",
    "RECONCILIATION",
    "PLANNING",
    "DESIGN",
    "IMPLEMENTATION",
    "VALIDATION",
    "PR REVIEW",
    "EXACT-HEAD CI",
    "INTEGRATION OR BLOCKED",
    "POST-INTEGRATION AUDIT",
    "ROADMAP SYNC",
    "HANDOFF",
)


class EngineeringRoundProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = PROTOCOL.read_text(encoding="utf-8")

    def test_exactly_twelve_ordered_stages(self):
        numbered = re.findall(r"(?m)^(\\d+)\\. \\*\\*([A-Z][A-Z -]+)\\*\\*", self.content)
        self.assertEqual(
            [(str(i), name) for i, name in enumerate(STAGES, start=1)],
            numbered,
        )

    def test_required_safety_boundaries(self):
        for phrase in (
            "NON-ENFORCING",
            "owner gate #56",
            "all open PRs",
            "changed-file",
            "UNKNOWN",
            "exact",
            "default branch",
            "No new DB",
            "no percent inflation",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), self.content.lower())

    def test_pilot_does_not_claim_acceptance(self):
        self.assertIn("Pilot acceptance checklist", self.content)
        self.assertIn("not a second task-status store", self.content)


if __name__ == "__main__":
    unittest.main()
