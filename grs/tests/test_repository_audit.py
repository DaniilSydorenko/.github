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

def manifest(repo_class: str, visibility: str = "public") -> dict:
    return {
        "schema": 1,
        "standard": {"version": 1},
        "repository": {"class": repo_class, "maturity": "active", "visibility": visibility},
        "portfolio": {"flagship": False, "pin_candidate": False},
    }

class RepositoryAuditTests(unittest.TestCase):
    def run_audit(self, repo_class: str, files: list[str], visibility: str = "public") -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "repository.json"
            manifest_path.write_text(json.dumps(manifest(repo_class, visibility)), encoding="utf-8")
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
        result = self.run_audit("profile", ["README.md", ".gitignore", ".github/workflows/secret-scan.yml"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SUMMARY: 0 FAIL", result.stdout)

    def test_profile_missing_secret_scan_fails(self) -> None:
        result = self.run_audit("profile", ["README.md", ".gitignore"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL: secret hygiene workflow", result.stdout)

    def test_oss_library_missing_governance_fails_truthfully(self) -> None:
        result = self.run_audit("oss-library", ["README.md", ".gitignore", "LICENSE.txt", ".github/workflows/secret-scan.yml"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL: SECURITY.md", result.stdout)
        self.assertIn("FAIL: CONTRIBUTING.md", result.stdout)
        self.assertIn("FAIL: PR template", result.stdout)
        self.assertIn("FAIL: issue taxonomy", result.stdout)

    def test_historical_requires_status_and_warns_on_gitignore(self) -> None:
        missing_status = self.run_audit("historical", [".github/workflows/secret-scan.yml"])
        self.assertNotEqual(missing_status.returncode, 0)
        self.assertIn("FAIL: README/status", missing_status.stdout)
        self.assertIn("WARN: .gitignore", missing_status.stdout)
        warning_only = self.run_audit("historical", ["README.md", ".github/workflows/secret-scan.yml"])
        self.assertEqual(warning_only.returncode, 0, warning_only.stdout + warning_only.stderr)
        self.assertIn("WARN: .gitignore", warning_only.stdout)
        self.assertIn("SUMMARY: 0 FAIL, 1 WARN", warning_only.stdout)

    def test_historical_requires_secret_hygiene(self) -> None:
        result = self.run_audit("historical", ["README.md", ".gitignore"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL: secret hygiene workflow", result.stdout)

    def test_oss_library_complete_surface_passes(self) -> None:
        result = self.run_audit("oss-library", ["README.md", ".gitignore", "LICENSE", ".github/workflows/secret-scan.yml", ".github/PULL_REQUEST_TEMPLATE.md", ".github/ISSUE_TEMPLATE/", "SECURITY.md", "CONTRIBUTING.md"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_engineering_labs_requires_governance_but_warns_community_docs(self) -> None:
        result = self.run_audit("engineering-labs", ["README.md", ".gitignore", "LICENSE", ".github/workflows/secret-scan.yml", ".github/PULL_REQUEST_TEMPLATE.md", ".github/ISSUE_TEMPLATE/"], visibility="private")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WARN: SECURITY.md", result.stdout)
        self.assertIn("WARN: CONTRIBUTING.md", result.stdout)

    def test_platform_missing_required_governance_fails(self) -> None:
        result = self.run_audit("platform", ["README.md", ".gitignore", ".github/workflows/secret-scan.yml"], visibility="private")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL: licensing decision", result.stdout)
        self.assertIn("FAIL: PR template", result.stdout)
        self.assertIn("FAIL: issue taxonomy", result.stdout)

    def test_private_knowledge_license_is_conditional(self) -> None:
        result = self.run_audit("knowledge", ["README.md", ".gitignore", ".github/workflows/secret-scan.yml"], visibility="private")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("licensing decision", result.stdout)
        self.assertIn("WARN: PR template", result.stdout)

    def test_public_knowledge_requires_license(self) -> None:
        result = self.run_audit("knowledge", ["README.md", ".gitignore", ".github/workflows/secret-scan.yml"], visibility="public")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL: licensing decision", result.stdout)

if __name__ == "__main__":
    unittest.main()
