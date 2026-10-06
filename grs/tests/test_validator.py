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

    def test_valid_profile_manifest_passes(self) -> None:
        result = self.run_fixture("valid-profile.json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS:", result.stdout)

    def test_unknown_class_fails(self) -> None:
        result = self.run_fixture("invalid-class.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository.class", result.stdout)

    def test_unknown_property_fails(self) -> None:
        result = self.run_fixture("invalid-extra-property.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported properties", result.stdout)


if __name__ == "__main__":
    unittest.main()
