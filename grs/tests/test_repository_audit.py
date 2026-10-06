#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDITOR = ROOT / "grs" / "audit_repository.py"

def manifest(repo_class: str) -> dict:
    return {
        "schema": 1,
        "standard": {"version": 1},
        "repository": {"class": repo_class, "maturity": "active", "visibility": "public"},
        "portfolio": {"flagship": False, "pin_candidate": False},
    }

class RepositoryAuditTests(unittest.TestCase):
    def run_audit(self, repo_class: str, files: list[str]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "repository.json"
            manifest_path.write_text(json.dumps(manifest(repo_class)), encoding="utf-8")
            for relative in files:
                path = root / relative
                if relative.endswith("/"):
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("", encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(AUDITOR), str(manifest_path), "--root", str(root)],
                check=False, capture_output=True, text=True,
            )

    def test_profile_minimum_passes(self) -> None:
        result = self.run_audit("profile", [
            "README.md", ".gitignore", ".github/workflows/secret-scan.yml",
        ])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SUMMARY: 0 FAIL", result.stdout)

    def test_profile_missing_secret_scan_fails(self) -> None:
        result = self.run_audit("profile", ["README.md", ".gitignore"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL: secret hygiene workflow", result.stdout)

    def test_oss_library_missing_governance_fails_truthfully(self) -> None:
        result = self.run_audit("oss-library", [
            "README.md", ".gitignore", "LICENSE.txt", ".github/workflows/secret-scan.yml",
        ])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL: SECURITY.md", result.stdout)
        self.assertIn("FAIL: CONTRIBUTING.md", result.stdout)
        self.assertIn("FAIL: PR template", result.stdout)
        self.assertIn("FAIL: issue taxonomy", result.stdout)

    def test_oss_library_complete_surface_passes(self) -> None:
        result = self.run_audit("oss-library", [
            "README.md", ".gitignore", "LICENSE", ".github/workflows/secret-scan.yml",
            ".github/PULL_REQUEST_TEMPLATE.md", ".github/ISSUE_TEMPLATE/",
            "SECURITY.md", "CONTRIBUTING.md",
        ])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == "__main__":
    unittest.main()
