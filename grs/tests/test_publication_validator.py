#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "grs" / "publication" / "validate_publication.py"

BASE = {
    "schema": 1,
    "repository": "DaniilSydorenko/example",
    "target": {
        "visibility": "public",
        "mode": "canonical-public",
        "status": "extraction-required",
    },
    "sensitive_surfaces": [
        {"path": "private/", "disposition": "externalize", "reason": "private overlay"}
    ],
    "history": {"audit_required": True, "rewrite_owner_gated": True},
    "gates": {
        "current_tree_public_safe": False,
        "history_public_safe": False,
        "exact_head_ci_green": False,
        "owner_visibility_approval": False,
    },
}


class PublicationValidatorTests(unittest.TestCase):
    def run_manifest(self, payload: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), str(path)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_valid_extraction_manifest_passes(self) -> None:
        result = self.run_manifest(BASE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unknown_property_fails_closed(self) -> None:
        payload = json.loads(json.dumps(BASE))
        payload["surprise"] = True
        result = self.run_manifest(payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported properties", result.stdout)

    def test_public_mode_requires_public_visibility(self) -> None:
        payload = json.loads(json.dumps(BASE))
        payload["target"]["visibility"] = "private"
        result = self.run_manifest(payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public publication modes require", result.stdout)

    def test_duplicate_surface_path_fails(self) -> None:
        payload = json.loads(json.dumps(BASE))
        payload["sensitive_surfaces"].append(dict(payload["sensitive_surfaces"][0]))
        result = self.run_manifest(payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate sensitive surface path", result.stdout)

    def test_ready_state_requires_technical_gates(self) -> None:
        payload = json.loads(json.dumps(BASE))
        payload["target"]["status"] = "ready-for-owner-gate"
        result = self.run_manifest(payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires green technical gates", result.stdout)

    def test_ready_state_cannot_skip_history_audit(self) -> None:
        payload = json.loads(json.dumps(BASE))
        payload["target"]["status"] = "ready-for-owner-gate"
        for key in ("current_tree_public_safe", "history_public_safe", "exact_head_ci_green"):
            payload["gates"][key] = True
        payload["history"]["audit_required"] = False
        result = self.run_manifest(payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("history.audit_required", result.stdout)

    def test_ready_state_cannot_disable_owner_history_rewrite_gate(self) -> None:
        payload = json.loads(json.dumps(BASE))
        payload["target"]["status"] = "ready-for-owner-gate"
        for key in ("current_tree_public_safe", "history_public_safe", "exact_head_ci_green"):
            payload["gates"][key] = True
        payload["history"]["rewrite_owner_gated"] = False
        result = self.run_manifest(payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("history.rewrite_owner_gated", result.stdout)

    def test_owner_approval_cannot_appear_early(self) -> None:
        payload = json.loads(json.dumps(BASE))
        payload["gates"]["owner_visibility_approval"] = True
        result = self.run_manifest(payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("only valid at ready-for-owner-gate", result.stdout)


if __name__ == "__main__":
    unittest.main()
