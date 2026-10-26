"""Synthetic one-step handoff tests: no Cursor keys, GitHub writes or model calls."""
import copy
import unittest

from sequential_handoff import preview_next_after_merge

A, B, C = "a" * 40, "b" * 40, "c" * 40


def baseline():
    return {
        "schema_version": 1,
        "repository": "example/private-product",
        "main": {"before_sha": A, "after_sha": A},
        "relevant_inventory_complete": True,
        "owner_authority_verified": True,
        "previous": {
            "pr_number": 40, "state": "closed", "merged": True,
            "head_sha": B, "merge_sha": C, "merge_on_default_verified": True,
            "ci": "SUCCESS", "secret_scan": "SUCCESS",
            "owner_merge_permission": "granted",
            "owner_visual_acceptance": "accepted", "deployment": "accepted",
        },
        "writer": {"inventory_complete": True, "status": "idle", "open_prs": []},
        "queue": [
            {"number": 41, "order": 1, "state": "closed", "accepted": True,
             "owner_approved": True, "owner_gate": False, "scope": "ui_low_risk",
             "allowed_paths": ["src/complete.py"], "dependencies": []},
            {"number": 42, "order": 2, "state": "open", "accepted": False,
             "owner_approved": True, "owner_gate": False, "scope": "ui_low_risk",
             "allowed_paths": ["src/next.py"], "dependencies": [
                 {"number": 41, "status": "accepted"}]},
        ],
    }


def open_pr(issue=42, number=45):
    return {"number": number, "issue_number": issue, "state": "open",
            "head_sha": B, "changed_paths": ["src/next.py"],
            "files_complete": True}


class SequentialHandoffTests(unittest.TestCase):
    def result(self, x, action):
        out = preview_next_after_merge(x)
        self.assertEqual(out["action"], action, out)
        for key in ("advisory_only",):
            self.assertIs(out[key], True)
        for key in ("provider_called", "cursor_launched", "cursor_launch_authorized",
                    "git_write", "merge_authorized", "owner_approval_bypassed"):
            self.assertIs(out[key], False)
        return out

    def test_ready_is_stable_owner_proposal_only(self):
        result = self.result(baseline(), "READY_FOR_OWNER_DISPATCH")
        self.assertEqual(result["next_issue_number"], 42)
        self.assertRegex(result["proposed_request_id"], r"^seq-[0-9a-f]{32}$")

    def test_repeated_hour_has_same_id(self):
        x = baseline()
        a = self.result(x, "READY_FOR_OWNER_DISPATCH")["proposed_request_id"]
        # Unrelated HEAD movement must not mint another agent/request.
        x["main"] = {"before_sha": B, "after_sha": B}
        b = self.result(x, "READY_FOR_OWNER_DISPATCH")["proposed_request_id"]
        self.assertEqual(a, b)

    def test_different_task_has_different_request(self):
        x = baseline()
        first = self.result(x, "READY_FOR_OWNER_DISPATCH")["proposed_request_id"]
        x["queue"][1]["number"] = 43
        self.assertNotEqual(first, self.result(x, "READY_FOR_OWNER_DISPATCH")["proposed_request_id"])

    def test_existing_pr_before_any_new_cursor(self):
        x = baseline()
        x["writer"]["open_prs"] = [open_pr()]
        d = self.result(x, "REUSE_EXISTING_PR")
        self.assertEqual(d["existing_pr_number"], 45)
        self.assertIsNone(d["proposed_request_id"])

    def test_other_open_pr_causes_wait_not_new_code(self):
        x = baseline()
        x["writer"]["open_prs"] = [open_pr(issue=88)]
        self.result(x, "WAIT")

    def test_two_competing_prs_for_issue_stops(self):
        x = baseline()
        x["writer"]["open_prs"] = [open_pr(), open_pr(number=46)]
        self.result(x, "STOP")

    def test_incomplete_inventory_stops(self):
        x = baseline()
        x["relevant_inventory_complete"] = False
        self.result(x, "STOP")
        x = baseline()
        x["writer"]["inventory_complete"] = False
        self.result(x, "STOP")

    def test_main_moves_mid_scan_stops(self):
        x = baseline()
        x["main"]["after_sha"] = B
        self.result(x, "STOP")

    def test_previous_not_merged_stops(self):
        x = baseline()
        x["previous"]["merged"] = False
        self.result(x, "STOP")

    def test_pr_merged_not_on_default_stops(self):
        x = baseline()
        x["previous"]["merge_on_default_verified"] = False
        self.result(x, "STOP")

    def test_failed_secret_scan_stops(self):
        x = baseline()
        x["previous"]["secret_scan"] = "PENDING"
        self.result(x, "STOP")

    def test_failed_ci_stops(self):
        x = baseline()
        x["previous"]["ci"] = "SKIPPED"
        self.result(x, "STOP")

    def test_unknown_previous_visual_acceptance_stops(self):
        x = baseline()
        x["previous"]["owner_visual_acceptance"] = "unknown"
        self.result(x, "STOP")

    def test_pending_previous_visual_acceptance_owner_gate(self):
        x = baseline()
        x["previous"]["owner_visual_acceptance"] = "pending"
        self.result(x, "OWNER_GATE")

    def test_pending_deployment_waits(self):
        x = baseline()
        x["previous"]["deployment"] = "pending"
        self.result(x, "WAIT")

    def test_owner_permission_missing_stops(self):
        x = baseline()
        x["owner_authority_verified"] = False
        self.result(x, "STOP")
        x = baseline()
        x["previous"]["owner_merge_permission"] = "unknown"
        self.result(x, "STOP")

    def test_owner_gated_next_issue_does_not_dispatch(self):
        x = baseline()
        x["queue"][1]["scope"] = "ui_owner_gated"
        self.result(x, "OWNER_GATE")

    def test_unapproved_next_issue_does_not_dispatch(self):
        x = baseline()
        x["queue"][1]["owner_approved"] = False
        self.result(x, "OWNER_GATE")

    def test_unknown_dependency_stops(self):
        x = baseline()
        x["queue"][1]["dependencies"][0]["status"] = "unknown"
        self.result(x, "STOP")

    def test_pending_dependency_waits(self):
        x = baseline()
        x["queue"][1]["dependencies"][0]["status"] = "pending"
        self.result(x, "WAIT")

    def test_active_writer_waits(self):
        x = baseline()
        x["writer"]["status"] = "active"
        self.result(x, "WAIT")

    def test_unknown_writer_stops(self):
        x = baseline()
        x["writer"]["status"] = None
        self.result(x, "STOP")

    def test_closed_not_accepted_is_not_skipped(self):
        x = baseline()
        x["queue"][0]["accepted"] = False
        self.result(x, "STOP")

    def test_unrelated_priority_blocker_is_not_skipped(self):
        x = baseline()
        x["queue"][0]["state"] = "open"
        x["queue"][0]["accepted"] = False
        x["queue"][0]["owner_gate"] = True
        self.assertEqual(self.result(x, "OWNER_GATE")["next_issue_number"], 41)

    def test_duplicate_issue_or_order_stops(self):
        for field, value in (("number", 41), ("order", 1)):
            x = baseline()
            x["queue"][1][field] = value
            self.result(x, "STOP")

    def test_queue_out_of_range_stops(self):
        x = baseline()
        x["queue"][1]["order"] = 100
        self.result(x, "STOP")

    def test_private_repo_source_not_part_of_result(self):
        x = baseline()
        d = self.result(x, "READY_FOR_OWNER_DISPATCH")
        self.assertNotIn(x["repository"], repr(d))

    def test_path_traversal_or_empty_scope_stops(self):
        for paths in ([], ["../secrets"], ["/root"], ["src/x", "src/x"]):
            x = baseline()
            x["queue"][1]["allowed_paths"] = paths
            self.result(x, "STOP")

    def test_queue_empty_is_no_work(self):
        x = baseline()
        x["queue"] = []
        self.result(x, "NO_READY_WORK")

    def test_all_accepted_is_no_work(self):
        x = baseline()
        x["queue"][1]["state"] = "closed"
        x["queue"][1]["accepted"] = True
        self.result(x, "NO_READY_WORK")

    def test_owner_boolean_forged_unknown_stops(self):
        x = baseline()
        x["queue"][1]["owner_approved"] = 1
        self.result(x, "STOP")

    def test_invalid_pr_metadata_stops(self):
        x = baseline()
        x["writer"]["open_prs"] = [dict(open_pr(), head_sha="stale")]
        self.result(x, "STOP")


if __name__ == "__main__":
    unittest.main()
