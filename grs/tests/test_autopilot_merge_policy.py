#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "grs" / "validate_autopilot_merge_policy.py"
POLICY = ROOT / "governance" / "autopilot-merge-policy.json"


class AutopilotMergePolicyTests(unittest.TestCase):
    def run_policy(self, data: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), str(path)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_live_policy_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(POLICY)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_visibility_cannot_become_automatic(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["operations"]["repository_visibility_change"] = "automatic"
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository_visibility_change must remain owner-only", result.stdout)

    def test_red_ci_merge_cannot_be_enabled(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["operations"]["merge_red_ci"] = "conditional"
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("merge_red_ci must remain forbidden", result.stdout)

    def test_exact_head_condition_is_required(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["merge_pr"]["required_conditions"].remove("exact-head-sha-verified")
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact-head-sha-verified", result.stdout)


if __name__ == "__main__":
    unittest.main()
