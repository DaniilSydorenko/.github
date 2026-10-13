"""Regression tests for fail-closed merge/branch lifecycle policy."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("lifecycle", ROOT / "grs/validate_pr_branch_lifecycle.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
POLICY = json.loads((ROOT / "governance/pr-branch-lifecycle-policy.json").read_text())


class LifecyclePolicyTests(unittest.TestCase):
    def test_current_policy(self):
        self.assertTrue(module.validate(POLICY))

    def test_merge_gate_cannot_be_removed(self):
        for gate in module.MERGE:
            with self.subTest(gate=gate):
                data = copy.deepcopy(POLICY)
                data["merge"]["required"].remove(gate)
                with self.assertRaises(ValueError):
                    module.validate(data)

    def test_delete_gate_cannot_be_removed(self):
        for gate in module.DELETE:
            with self.subTest(gate=gate):
                data = copy.deepcopy(POLICY)
                data["branch_deletion"]["required"].remove(gate)
                with self.assertRaises(ValueError):
                    module.validate(data)

    def test_no_automatic_rollout(self):
        data = copy.deepcopy(POLICY)
        data["rollout"] = "enforced"
        with self.assertRaises(ValueError):
            module.validate(data)

    def test_no_age_only_cleanup(self):
        data = copy.deepcopy(POLICY)
        data["branch_deletion"]["forbidden"].remove("age-only")
        with self.assertRaises(ValueError):
            module.validate(data)

    def test_no_draft_merge(self):
        data = copy.deepcopy(POLICY)
        data["merge"]["forbidden"].remove("draft")
        with self.assertRaises(ValueError):
            module.validate(data)

    def test_unmerged_branch_retention(self):
        data = copy.deepcopy(POLICY)
        data["retention"]["unmerged_branch"] = "delete-after-30-days"
        with self.assertRaises(ValueError):
            module.validate(data)


if __name__ == "__main__":
    unittest.main()
