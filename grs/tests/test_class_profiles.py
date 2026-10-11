#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDITOR_PATH = ROOT / "grs" / "audit_repository.py"

spec = importlib.util.spec_from_file_location("audit_repository", AUDITOR_PATH)
audit_repository = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(audit_repository)


class ClassProfileTests(unittest.TestCase):
    def test_all_manifest_classes_have_machine_readable_profiles(self) -> None:
        profiles = audit_repository.load_profiles()
        self.assertEqual(
            set(profiles["classes"]),
            {
                "profile",
                "oss-library",
                "product",
                "engineering-labs",
                "knowledge",
                "platform",
                "historical",
            },
        )

    def test_public_knowledge_adds_required_license_control(self) -> None:
        profiles = audit_repository.load_profiles()
        controls = audit_repository.selected_controls(profiles, "knowledge", "public")
        matches = [control for control in controls if control["name"] == "licensing decision"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["level"], "REQUIRED")

    def test_private_knowledge_does_not_require_license_control(self) -> None:
        profiles = audit_repository.load_profiles()
        controls = audit_repository.selected_controls(profiles, "knowledge", "private")
        self.assertNotIn("licensing decision", {control["name"] for control in controls})

    def test_security_baseline_is_required_for_every_class(self) -> None:
        profiles = audit_repository.load_profiles()
        for repo_class, controls in profiles["classes"].items():
            by_name = {control["name"]: control for control in controls}
            self.assertIn("secret hygiene workflow", by_name, repo_class)
            self.assertEqual(by_name["secret hygiene workflow"]["level"], "REQUIRED", repo_class)


if __name__ == "__main__":
    unittest.main()
