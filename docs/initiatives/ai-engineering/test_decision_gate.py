"""Synthetic regression cases only; never contain private or mutable fleet data."""

import unittest

from decision_gate import decide


SHA_A = "a" * 40
SHA_B = "b" * 40


def sample(**overrides):
    evidence = {
        "default_sha": SHA_A,
        "checked_sha": SHA_A,
        "inventory_complete": True,
        "issue_state": "open",
        "accepted_commit": None,
        "accepted_proof": None,
        "related_prs": [],
        "dependencies": [],
        "writer": "idle",
        "scope": "allowed",
        "owner_permission": "granted",
        "owner_gate": False,
        "external": "clear",
    }
    evidence.update(overrides)
    return {"schema_version": 1, "repository": "example/test",
            "issue": "https://github.com/example/test/issues/42", "evidence": evidence}


class DecisionGateTests(unittest.TestCase):
    def assert_status(self, expected, **overrides):
        result = decide(sample(**overrides))
        self.assertEqual(result["status"], expected)
        self.assertFalse(result["launched"])

    def test_truly_ready_bounded_issue(self):
        self.assert_status("READY")

    def test_stale_haversine_candidate_now_accepted(self):
        self.assert_status("ALREADY_ACCEPTED", accepted_commit=SHA_B,
                           accepted_proof="https://github.com/example/test/pull/190")

    def test_old_haversine_200_candidate_replaced_by_201(self):
        self.assert_status("SUPERSEDED", superseded_by={
            "accepted_sha": SHA_B,
            "ref": "https://github.com/example/test/pull/190",
            "reason": "Owner selected 2.0.1 instead of 2.0.0"})

    def test_unverified_supersession_is_not_accepted(self):
        self.assert_status("NEEDS_EVIDENCE", superseded_by={
            "ref": "https://github.com/example/test/pull/190",
            "reason": "Changed version"})

    def test_closed_issue_without_accepted_proof_is_not_done(self):
        self.assert_status("NEEDS_EVIDENCE", issue_state="closed")

    def test_contradictory_accepted_and_superseded_fails_closed(self):
        self.assert_status("NEEDS_EVIDENCE", accepted_commit=SHA_B,
                           accepted_proof="https://github.com/example/test/pull/190",
                           superseded_by={"accepted_sha": SHA_A,
                                          "ref": "https://github.com/example/test/pull/191",
                                          "reason": "Owner changed the target"})

    def test_invalid_proof_page_is_not_an_accepted_commit(self):
        self.assert_status("NEEDS_EVIDENCE", accepted_commit=SHA_B,
                           accepted_proof="https://github.com/example/test/tree/main")
        self.assert_status("NEEDS_EVIDENCE", accepted_commit=SHA_B,
                           accepted_proof="https://github.com/example/test/issues/1")

    def test_unrelated_repo_prefix_and_pr_trailing_path_are_invalid(self):
        self.assert_status("NEEDS_EVIDENCE", accepted_commit=SHA_B,
                           accepted_proof="https://github.com/example/test-other/pull/190")
        self.assert_status("NEEDS_EVIDENCE", accepted_commit=SHA_B,
                           accepted_proof="https://github.com/example/test/pull/190/files")

    def test_immutable_commit_link_can_support_accepted_claim_shape(self):
        self.assert_status("ALREADY_ACCEPTED", accepted_commit=SHA_B,
                           accepted_proof="https://github.com/example/test/commit/" + SHA_B)

    def test_supersession_requires_specific_pr_or_commit_ref(self):
        self.assert_status("NEEDS_EVIDENCE", superseded_by={
            "accepted_sha": SHA_B,
            "ref": "https://github.com/example/test/tree/main",
            "reason": "Approved change"})

    def test_accepted_claim_without_proof_is_not_done(self):
        self.assert_status("NEEDS_EVIDENCE", accepted_commit=SHA_B)

    def test_existing_ladvero_pr_blocks_duplicate_task(self):
        self.assert_status("EXISTING_PR", related_prs=[
            {"number": 212, "relation": "same_outcome", "head_sha": SHA_B}])

    def test_ladvero_same_file_overlap(self):
        self.assert_status("WAITING_DEPENDENCY", related_prs=[
            {"number": 216, "relation": "overlapping_paths", "head_sha": SHA_B}])

    def test_handbook_stack_waits_for_parent(self):
        self.assert_status("WAITING_DEPENDENCY", related_prs=[
            {"number": 64, "relation": "stack_dependency", "head_sha": SHA_B}])

    def test_pending_dependency_does_not_block_other_tasks_globally(self):
        self.assert_status("WAITING_DEPENDENCY", dependencies=[{"ref": "#154", "state": "pending"}])
        self.assert_status("READY", dependencies=[{"ref": "#154", "state": "accepted"}])

    def test_unverified_dependency(self):
        self.assert_status("NEEDS_EVIDENCE", dependencies=[{"ref": "#154", "state": "unknown"}])

    def test_career_publication_owner_gate(self):
        self.assert_status("OWNER_GATE", scope="owner_gated", owner_permission="granted")

    def test_labs_learner_task_cannot_be_completed_by_agent(self):
        self.assert_status("UNSAFE", scope="forbidden")

    def test_unknown_collaboration_state(self):
        self.assert_status("NEEDS_EVIDENCE", writer="unknown")
        self.assert_status("WAITING_DEPENDENCY", writer="active")

    def test_current_branch_changed_since_observation(self):
        self.assert_status("NEEDS_EVIDENCE", checked_sha=SHA_B)

    def test_pr_inventory_incomplete(self):
        self.assert_status("NEEDS_EVIDENCE", inventory_complete=False)

    def test_unknown_pr_relation_fails_closed(self):
        self.assert_status("NEEDS_EVIDENCE", related_prs=[
            {"number": 999, "relation": "looks_old", "head_sha": SHA_B}])

    def test_external_failure_is_not_blindly_retried(self):
        self.assert_status("EXTERNAL_BLOCKED", external="blocked")

    def test_missing_owner_permission(self):
        self.assert_status("OWNER_GATE", owner_permission="missing")

    def test_missing_field_is_not_ready(self):
        x = sample()
        del x["evidence"]["related_prs"]
        self.assertEqual(decide(x)["status"], "NEEDS_EVIDENCE")

    def test_invalid_issue_link_is_not_ready(self):
        x = sample()
        x["issue"] = "https://github.com/different/repo/issues/7"
        self.assertEqual(decide(x)["status"], "NEEDS_EVIDENCE")

    def test_unrelated_open_pr_does_not_globally_block(self):
        self.assert_status("READY", related_prs=[
            {"number": 88, "relation": "unrelated", "head_sha": SHA_B}])


if __name__ == "__main__":
    unittest.main()
