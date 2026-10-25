"""Read-only Issue #119 composition fixtures; do not launch Cursor or mutate GitHub."""
from copy import deepcopy
import unittest

from preview_one import preview_one

A, B, C = "a" * 40, "b" * 40, "c" * 40
REPO = "example/test"
ISSUE = f"https://github.com/{REPO}/issues/42"
PATH = "src/feature.py"


def fixture(include_pr=True):
    raw = []
    semantic_prs = []
    observed_prs = []
    decision_prs = []
    if include_pr:
        raw = [{
            "number": 212, "state": "open", "head_sha": B, "base_sha": A,
            "changed_files_observed": [PATH], "changed_files_pagination_complete": True,
        }]
        observed_prs = [{"number": 212, "state": "open", "head_sha": B, "base_sha": A}]
        decision_prs = [{"number": 212, "head_sha": B, "relation": "same_outcome"}]
        semantic_prs = [{
            "number": 212, "url": f"https://github.com/{REPO}/pull/212",
            "state": "open", "merged": False,
            "head_sha": B, "observed_head_sha": B,
            "base_sha": A, "observed_base_sha": A,
            "changed_paths": [PATH], "changed_paths_complete": True,
            "relation": "PARTIAL", "reviewer_confirmed": True,
            "owner_gate": False, "writer_active": False, "stack_parent": None,
        }]

    return {
        "schema_version": 1,
        "collector": {
            "status": "OBSERVED", "missing_capabilities": [], "warnings": [],
            "observed_facts": {
                "repo": REPO, "issue_number": 42, "issue_state": "open", "default_sha": A,
                "linked_pr_inventory_truncated": False,
                "related_prs_files_pagination_complete": True,
                "related_prs": raw,
            },
        },
        "observed": {
            "repo": REPO, "issue_number": 42, "issue_state": "open", "default_sha": A,
            "related_inventory_complete": True, "related_prs": observed_prs,
            "accepted_shas": [],
        },
        "task": {
            "repository": REPO, "issue": ISSUE,
            "evidence": {
                "default_sha": A, "checked_sha": A, "inventory_complete": True,
                "issue_state": "open", "accepted_commit": None, "accepted_proof": None,
                "related_prs": decision_prs, "dependencies": [],
                "writer": "idle", "scope": "allowed", "owner_permission": "granted",
                "owner_gate": False, "external": "clear",
            },
        },
        "semantic": {
            "schema_version": 1, "repository": REPO, "issue_url": ISSUE,
            "issue_number": 42, "issue_state": "open",
            "default_sha": A, "observed_default_sha": A,
            "inventory_complete": True, "semantic_attestations_complete": True,
            "permission": "granted", "owner_gate": False, "writer": "idle",
            "proposed_paths": [PATH], "prs": semantic_prs,
        },
    }


class PreviewTests(unittest.TestCase):
    def check(self, data, action):
        r = preview_one(data)
        self.assertEqual(r["decision"], action, r)
        self.assertFalse(r["launched"])
        self.assertFalse(r["execution_authorized"])
        self.assertFalse(r["provider_called"])
        return r

    def test_existing_pr_first(self):
        r = self.check(fixture(), "REUSE_EXISTING_PR")
        self.assertEqual(r["selected_pr"], 212)
        self.assertEqual(r["observed_sha"], A)

    def test_no_pr_is_only_an_owner_dispatch_proposal(self):
        self.check(fixture(include_pr=False), "READY_FOR_OWNER_DISPATCH")

    def test_collector_partial_or_missing_blocks(self):
        for status in ("PARTIAL", "NEEDS_EVIDENCE", None):
            with self.subTest(status=status):
                d = fixture()
                d["collector"]["status"] = status
                self.check(d, "STOP")

    def test_collector_rate_limited_blocks(self):
        d = fixture()
        d["collector"]["missing_capabilities"] = ["github_api_rate_limit_or_permission_denied"]
        self.check(d, "STOP")

    def test_collector_warning_blocks(self):
        d = fixture()
        d["collector"]["warnings"] = ["PR head changed"]
        self.check(d, "STOP")

    def test_cross_repo_owner_mismatch_blocks(self):
        d = fixture()
        d["semantic"]["repository"] = "other/repo"
        self.check(d, "STOP")

    def test_issue_identity_mismatch_blocks(self):
        d = fixture()
        d["collector"]["observed_facts"]["issue_number"] = 41
        self.check(d, "STOP")

    def test_stale_default_branch_blocks(self):
        d = fixture()
        d["task"]["evidence"]["checked_sha"] = C
        self.check(d, "STOP")

    def test_collector_vs_observed_default_sha_blocks(self):
        d = fixture()
        d["collector"]["observed_facts"]["default_sha"] = C
        self.check(d, "STOP")

    def test_untrusted_related_inventory_flag_blocks(self):
        d = fixture()
        d["observed"]["related_inventory_complete"] = None
        self.check(d, "STOP")

    def test_extra_related_pr_is_not_ignored(self):
        d = fixture()
        d["collector"]["observed_facts"]["related_prs"].append({
            "number": 216, "state": "open", "head_sha": C,
            "base_sha": A, "changed_files_observed": ["other.py"],
            "changed_files_pagination_complete": True,
        })
        self.check(d, "STOP")

    def test_incomplete_pr_files_reject(self):
        d = fixture()
        d["collector"]["observed_facts"]["related_prs"][0][
            "changed_files_pagination_complete"] = False
        self.check(d, "STOP")

    def test_stale_pr_head_reject(self):
        d = fixture()
        d["collector"]["observed_facts"]["related_prs"][0]["head_sha"] = C
        self.check(d, "STOP")

    def test_stale_pr_base_reject(self):
        d = fixture()
        d["collector"]["observed_facts"]["related_prs"][0]["base_sha"] = C
        self.check(d, "STOP")

    def test_changed_pr_paths_reject(self):
        d = fixture()
        d["collector"]["observed_facts"]["related_prs"][0]["changed_files_observed"] = [
            "src/other.py"]
        self.check(d, "STOP")

    def test_owner_gate_from_decision(self):
        d = fixture()
        d["task"]["evidence"]["owner_gate"] = True
        self.check(d, "OWNER_GATE")

    def test_owner_gate_from_semantic(self):
        d = fixture()
        d["semantic"]["owner_gate"] = True
        self.check(d, "OWNER_GATE")

    def test_active_writer_blocks(self):
        d = fixture()
        d["semantic"]["prs"][0]["writer_active"] = True
        self.check(d, "WAIT")

    def test_dependency_pending_waits(self):
        d = fixture()
        d["task"]["evidence"]["dependencies"] = [{"ref": "#99", "state": "pending"}]
        self.check(d, "WAIT")

    def test_missing_owner_permission_gate(self):
        d = fixture()
        d["semantic"]["permission"] = "missing"
        self.check(d, "OWNER_GATE")

    def test_semantic_no_same_outcome_conflict_is_not_dispatch(self):
        d = fixture()
        d["semantic"]["prs"][0]["relation"] = "UNRELATED"
        self.check(d, "WAIT")  # conflicting path blocks despite semantic 'unrelated'

    def test_no_unsigned_owner_assertions(self):
        d = fixture()
        d["semantic"]["prs"][0]["reviewer_confirmed"] = False
        self.check(d, "STOP")

    def test_proposed_task_already_accepted_requires_proof(self):
        d = fixture(include_pr=False)
        d["task"]["evidence"]["accepted_commit"] = C
        d["task"]["evidence"]["accepted_proof"] = f"https://github.com/{REPO}/commit/{C}"
        self.check(d, "STOP")  # accepted SHA absent from independently observed accepted set

    def test_career_private_forbidden_scope_stops(self):
        d = fixture(include_pr=False)
        d["task"]["evidence"]["scope"] = "forbidden"
        self.check(d, "STOP")

    def test_collector_is_not_launch_authority(self):
        d = fixture(include_pr=False)
        self.assertIs(self.check(d, "READY_FOR_OWNER_DISPATCH")["execution_authorized"], False)


if __name__ == "__main__":
    unittest.main()
