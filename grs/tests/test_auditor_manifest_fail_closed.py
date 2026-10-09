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
    def run_audit(self, repo_class: object, visibility: object, *, schema: object = 1, standard_version: object = 1, omit: str | None = None) -> subprocess.CompletedProcess[str]:
        data = {
            "schema": schema,
            "standard": {"version": standard_version},
            "repository": {"class": repo_class, "maturity": "active", "visibility": visibility},
            "portfolio": {"flagship": False, "pin_candidate": False},
        }
        if omit == "schema":
            del data["schema"]
        elif omit == "standard.version":
            del data["standard"]["version"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ("README.md", ".gitignore", ".github/workflows/secret-scan.yml"):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")
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

    def test_supported_versions_pass_with_complete_profile_surface(self) -> None:
        result = self.run_audit("profile", "public")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unsupported_schema_versions_fail_closed(self) -> None:
        for value in (2, True, 1.0, "1", None):
            with self.subTest(value=value):
                result = self.run_audit("profile", "public", schema=value)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("FAIL: unsupported manifest schema version", result.stdout)

    def test_unsupported_standard_versions_fail_closed(self) -> None:
        for value in (2, True, 1.0, "1", None):
            with self.subTest(value=value):
                result = self.run_audit("profile", "public", standard_version=value)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("FAIL: unsupported GRS standard version", result.stdout)

    def test_missing_schema_version_fails_closed(self) -> None:
        result = self.run_audit("profile", "public", omit="schema")
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_missing_standard_version_fails_closed(self) -> None:
        result = self.run_audit("profile", "public", omit="standard.version")
        self.assertNotEqual(result.returncode, 0, result.stdout)

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
