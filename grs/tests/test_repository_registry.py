#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "grs" / "validate_repository_registry.py"
REGISTRY = ROOT / "governance" / "repository-registry.json"


class RepositoryRegistryTests(unittest.TestCase):
    def run_registry(self, data: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), str(path)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_live_registry_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(REGISTRY)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_duplicate_repository_fails(self) -> None:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        data["repositories"].append(dict(data["repositories"][0]))
        result = self.run_registry(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository names must be unique", result.stdout)

    def test_mutable_progress_is_forbidden(self) -> None:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        data["repositories"][0]["progress"] = 99
        result = self.run_registry(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not duplicate mutable status", result.stdout)

    def test_all_seven_repositories_are_required(self) -> None:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        data["repositories"] = data["repositories"][:-1]
        result = self.run_registry(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("registry scope mismatch", result.stdout)


if __name__ == "__main__":
    unittest.main()
