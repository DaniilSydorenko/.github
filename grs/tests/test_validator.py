#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "grs" / "validator.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ValidatorCliTests(unittest.TestCase):
    def run_fixture(self, name: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(FIXTURES / name)],
            check=False,
            capture_output=True,
            text=True,
        )

    def assert_fails(self, name: str, message: str) -> None:
        result = self.run_fixture(name)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stdout)

    def test_valid_profile_manifest_passes(self) -> None:
        result = self.run_fixture("valid-profile.json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS:", result.stdout)

    def test_unknown_class_fails(self) -> None:
        self.assert_fails("invalid-class.json", "repository.class")

    def test_unknown_property_fails(self) -> None:
        self.assert_fails("invalid-extra-property.json", "unsupported properties")

    def test_missing_portfolio_fails(self) -> None:
        self.assert_fails("invalid-missing-portfolio.json", "repository and portfolio objects are required")

    def test_boolean_type_fails(self) -> None:
        self.assert_fails("invalid-boolean-type.json", "portfolio.flagship must be boolean")

    def test_schema_version_fails(self) -> None:
        self.assert_fails("invalid-schema-version.json", "schema must equal 1")

    def test_schema_type_fails(self) -> None:
        self.assert_fails("invalid-schema-number-type.json", "schema must equal 1")

    def test_standard_version_type_fails(self) -> None:
        self.assert_fails("invalid-standard-version-type.json", "standard.version must equal 1")


if __name__ == "__main__":
    unittest.main()
