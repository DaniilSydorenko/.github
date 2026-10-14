#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "grs" / "validate_autopilot_merge_policy.py"
POLICY = ROOT / "governance" / "autopilot-merge-policy.json"


class AutopilotMergePolicyTests(unittest.TestCase):
    def run_policy(self, data: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), str(path)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_live_policy_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(POLICY)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_visibility_cannot_become_automatic(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["operations"]["repository_visibility_change"] = "automatic"
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository_visibility_change must remain owner-only", result.stdout)

    def test_red_ci_merge_cannot_be_enabled(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["operations"]["merge_red_ci"] = "conditional"
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("merge_red_ci must remain forbidden", result.stdout)

    def test_exact_head_condition_is_required(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["merge_pr"]["required_conditions"].remove("exact-head-sha-verified")
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact-head-sha-verified", result.stdout)

    def test_history_rewrite_cannot_become_automatic(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["operations"]["history_rewrite"] = "automatic"
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("history_rewrite must remain owner-only", result.stdout)

    def test_credential_change_cannot_become_automatic(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["operations"]["credential_rotation_or_revocation"] = "automatic"
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("credential_rotation_or_revocation must remain owner-only", result.stdout)

    def test_stable_release_publish_remains_owner_only(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["operations"]["stable_release_publish"] = "automatic"
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stable_release_publish must remain owner-only", result.stdout)

    def test_other_worker_roadmap_remains_forbidden(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["operations"]["other_worker_roadmap"] = "conditional"
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("other_worker_roadmap must remain forbidden", result.stdout)

    def test_changed_head_merge_remains_forbidden(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["operations"]["merge_changed_head"] = "conditional"
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("merge_changed_head must remain forbidden", result.stdout)

    def test_domain_product_code_remains_domain_owner_only(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["operations"]["domain_product_code"] = "automatic"
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("domain_product_code must remain domain-owner-only", result.stdout)

    def test_required_ci_green_condition_is_required(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["merge_pr"]["required_conditions"].remove("required-ci-green")
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required-ci-green", result.stdout)

    def test_duplicate_required_condition_fails_closed(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["merge_pr"]["required_conditions"].append("required-ci-green")
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not contain duplicates", result.stdout)

    def test_unknown_top_level_policy_property_fails_closed(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["future_implicit_authority"] = True
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported properties", result.stdout)

    def test_current_run_authorization_must_remain_explicit(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["merge_pr"]["required_conditions"].remove("current-run-explicit-authorization")
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("current-run-explicit-authorization", result.stdout)

    def test_draft_pr_cannot_become_merge_eligible(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["merge_pr"]["required_conditions"].remove("not-draft")
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not-draft", result.stdout)

    def test_domain_collision_gate_cannot_be_removed(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["merge_pr"]["required_conditions"].remove("no-domain-ownership-conflict")
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no-domain-ownership-conflict", result.stdout)

    def test_worker_roadmap_collision_gate_cannot_be_removed(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["merge_pr"]["required_conditions"].remove("no-worker-roadmap-collision")
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no-worker-roadmap-collision", result.stdout)

    def test_owner_gate_cannot_be_removed(self) -> None:
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        data["merge_pr"]["required_conditions"].remove("no-owner-gated-operation")
        result = self.run_policy(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no-owner-gated-operation", result.stdout)



if __name__ == "__main__":
    unittest.main()
