"""Regression coverage for unsupported GRS auditor manifest values."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

AUDITOR = Path(__file__).resolve().parents[1] / "audit_repository.py"

class FailClosedManifestTests(unittest.TestCase):
    def run_audit(self, repo_class: object, visibility: object) -> subprocess.CompletedProcess[str]:
        data = {
            "schema": 1,
            "standard": {"version": 1},
            "repository": {"class": repo_class, "maturity": "active", "visibility": visibility},
            "portfolio": {"flagship": False, "pin_candidate": False},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "repository.json"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(AUDITOR), str(manifest), "--root", str(root)],
                capture_output=True, text=True, check=False,
            )

    def assert_fails(self, repo_class: object, visibility: object, expected_message: str) -> None:
        result = self.run_audit(repo_class, visibility)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(expected_message, result.stdout)

    def test_unknown_class(self) -> None:
        self.assert_fails("unsupported-class", "private", "FAIL: unsupported repository class")

    def test_invalid_visibility(self) -> None:
        self.assert_fails("knowledge", "internal", "FAIL: unsupported repository visibility")

    def test_non_string_class(self) -> None:
        self.assert_fails(["profile"], "public", "FAIL: unsupported repository class")

    def test_non_string_visibility(self) -> None:
        self.assert_fails("knowledge", ["public"], "FAIL: unsupported repository visibility")

if __name__ == "__main__":
    unittest.main()
