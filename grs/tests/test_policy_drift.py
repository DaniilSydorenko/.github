#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRIFT_PATH = ROOT / "grs" / "check_policy_drift.py"

spec = importlib.util.spec_from_file_location("check_policy_drift", DRIFT_PATH)
check_policy_drift = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(check_policy_drift)


def schema(classes: list[str]) -> dict:
    return {
        "properties": {
            "repository": {
                "properties": {
                    "class": {
                        "enum": classes,
                    }
                }
            }
        }
    }


def profiles(classes: list[str]) -> dict:
    return {
        "version": 1,
        "classes": {name: [] for name in classes},
        "conditional": [],
    }


class PolicyDriftTests(unittest.TestCase):
    def test_live_policy_sources_are_synchronized(self) -> None:
        result = check_policy_drift.run(
            ROOT / "grs" / "repository.schema.json",
            ROOT / "grs" / "classes" / "profiles.json",
            ROOT / "grs" / "validator.py",
            ROOT / "grs" / "pilots",
        )
        self.assertEqual(result, 0)

    def test_profile_taxonomy_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_path = root / "schema.json"
            profiles_path = root / "profiles.json"
            schema_path.write_text(json.dumps(schema(["profile", "platform"])), encoding="utf-8")
            profiles_path.write_text(json.dumps(profiles(["profile"])), encoding="utf-8")

            self.assertEqual(
                check_policy_drift.schema_classes(schema_path),
                {"profile", "platform"},
            )
            self.assertEqual(
                check_policy_drift.profile_classes(profiles_path),
                {"profile"},
            )
            self.assertTrue(
                check_policy_drift.compare(
                    "class profiles",
                    {"profile", "platform"},
                    {"profile"},
                )
            )

    def test_unknown_pilot_class_is_detectable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pilot = root / "example.repository.json"
            pilot.write_text(
                json.dumps({"repository": {"class": "unknown"}}),
                encoding="utf-8",
            )
            self.assertEqual(
                check_policy_drift.pilot_classes(root),
                {"example.repository.json": "unknown"},
            )


if __name__ == "__main__":
    unittest.main()
