#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "grs" / "audit_repository_registry_drift.py"
SPEC = importlib.util.spec_from_file_location("registry_drift", MODULE_PATH)
assert SPEC and SPEC.loader
registry_drift = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry_drift)


def sample_registry() -> dict:
    return {
        "repositories": [
            {
                "repository": "DaniilSydorenko/example",
                "default_branch": "main",
                "discovery": {
                    "roadmap": "ROADMAP.md",
                    "agent": None,
                    "authority": "AUTHORITY.md",
                    "governance": None,
                    "specialized_trackers": [
                        {"role": "execution", "path": "TASKS.md"},
                        {"role": "duplicate", "path": "TASKS.md"},
                    ],
                },
            }
        ]
    }


class RepositoryRegistryDriftTests(unittest.TestCase):
    def test_discovery_paths_are_deduplicated_without_reordering(self) -> None:
        paths = registry_drift.discovery_paths(sample_registry()["repositories"][0])
        self.assertEqual(paths, ["ROADMAP.md", "AUTHORITY.md", "TASKS.md"])

    def test_clean_registry_has_no_findings(self) -> None:
        responses = {
            "/repos/DaniilSydorenko/example": (200, {"default_branch": "main"}),
            "/repos/DaniilSydorenko/example/contents/ROADMAP.md?ref=main": (200, {}),
            "/repos/DaniilSydorenko/example/contents/AUTHORITY.md?ref=main": (200, {}),
            "/repos/DaniilSydorenko/example/contents/TASKS.md?ref=main": (200, {}),
        }
        findings = registry_drift.audit_registry(
            sample_registry(), lambda path: responses.get(path, (500, None))
        )
        self.assertEqual(findings, [])

    def test_default_branch_drift_is_reported(self) -> None:
        responses = {
            "/repos/DaniilSydorenko/example": (200, {"default_branch": "master"}),
            "/repos/DaniilSydorenko/example/contents/ROADMAP.md?ref=main": (200, {}),
            "/repos/DaniilSydorenko/example/contents/AUTHORITY.md?ref=main": (200, {}),
            "/repos/DaniilSydorenko/example/contents/TASKS.md?ref=main": (200, {}),
        }
        findings = registry_drift.audit_registry(
            sample_registry(), lambda path: responses.get(path, (500, None))
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "drift")
        self.assertIn("default branch drift", findings[0].detail)

    def test_missing_pointer_is_reported_as_drift(self) -> None:
        responses = {
            "/repos/DaniilSydorenko/example": (200, {"default_branch": "main"}),
            "/repos/DaniilSydorenko/example/contents/ROADMAP.md?ref=main": (404, {}),
            "/repos/DaniilSydorenko/example/contents/AUTHORITY.md?ref=main": (200, {}),
            "/repos/DaniilSydorenko/example/contents/TASKS.md?ref=main": (200, {}),
        }
        findings = registry_drift.audit_registry(
            sample_registry(), lambda path: responses.get(path, (500, None))
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "drift")
        self.assertIn("ROADMAP.md", findings[0].detail)

    def test_unreadable_private_repository_is_operational_error_not_false_drift(self) -> None:
        findings = registry_drift.audit_registry(
            sample_registry(), lambda _path: (404, None)
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "operational")
        self.assertIn("not readable", findings[0].detail)

    def test_api_failure_is_fail_closed(self) -> None:
        findings = registry_drift.audit_registry(
            sample_registry(), lambda _path: (503, None)
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "operational")
        self.assertIn("HTTP 503", findings[0].detail)


if __name__ == "__main__":
    unittest.main()
