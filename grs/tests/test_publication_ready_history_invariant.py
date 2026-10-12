#!/usr/bin/env python3
"""Regression guard: publication readiness cannot bypass history safeguards."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VALIDATOR = Path(__file__).resolve().parents[2] / "grs" / "publication" / "validate_publication.py"


class ReadyHistoryInvariantTests(unittest.TestCase):
    def validate(self, audit_required: bool, rewrite_owner_gated: bool) -> subprocess.CompletedProcess[str]:
        payload = {
            "schema": 1,
            "repository": "example/publication",
            "target": {"visibility": "public", "mode": "canonical-public", "status": "ready-for-owner-gate"},
            "sensitive_surfaces": [],
            "history": {"audit_required": audit_required, "rewrite_owner_gated": rewrite_owner_gated},
            "gates": {
                "current_tree_public_safe": True,
                "history_public_safe": True,
                "exact_head_ci_green": True,
                "owner_visibility_approval": False,
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run([sys.executable, str(VALIDATOR), str(path)], capture_output=True, text=True)

    def test_both_history_guards_required_at_ready_gate(self) -> None:
        for audit, rewrite in ((False, True), (True, False), (False, False)):
            with self.subTest(audit=audit, rewrite=rewrite):
                result = self.validate(audit, rewrite)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("requires history audit", result.stdout)

    def test_valid_ready_state_still_passes(self) -> None:
        result = self.validate(True, True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
