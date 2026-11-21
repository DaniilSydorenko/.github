#!/usr/bin/env python3
"""Regression guard for the reviewed cross-PR CI overlay (no network or model)."""
from pathlib import Path
import re
import unittest

WORKFLOW = Path(__file__).resolve().parents[3] / ".github/workflows/ai-eng-singleton-verify.yml"
REVIEWED_SHA = "40d448cc5e9b95740643a6133343e73f1d869009"


class CrossPrOverlayPinTests(unittest.TestCase):
    def test_overlay_requires_exact_reviewed_commit(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(f"expected_overlay_sha={REVIEWED_SHA}", workflow)
        self.assertIn('actual_overlay_sha="$(git rev-parse FETCH_HEAD)"', workflow)
        self.assertIn('if [ "$actual_overlay_sha" != "$expected_overlay_sha" ]; then', workflow)
        guarded = workflow.split('if [ "$actual_overlay_sha" != "$expected_overlay_sha" ]; then', 1)[1]
        self.assertRegex(guarded.split("fi", 1)[0], r"exit 1")
        self.assertIn('git show "$expected_overlay_sha":', workflow)
        self.assertNotIn("git show FETCH_HEAD:", workflow)

    def test_pin_is_full_lowercase_sha(self):
        self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{40}", REVIEWED_SHA))


if __name__ == "__main__":
    unittest.main()
