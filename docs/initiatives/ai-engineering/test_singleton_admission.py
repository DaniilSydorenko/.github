"""Offline negative proofs for gate logic; NOT a real atomic-lock acceptance test."""

from copy import deepcopy
import unittest

from singleton_admission import evaluate

A = "a" * 40
B = "b" * 40


def baseline():
    return {
        "evidence_complete": True,
        "budget_controls_verified": True,
        "cursor_on_demand_disabled": True,
        "external_billing_excluded": True,
        "model_allowlisted": True,
        "subagents_disabled": True,
        "launch_routes_exclusive": True,
        "request_id": "req-issue-42",
        "prior_request_ids": [],
        "lease": {"verified_atomic": True, "state": "FREE", "owner_request_id": None},
        "provider_run_inventory_complete": True,
        "ambiguous_previous_launch": False,
        "active_run_ids": [],
        "scope_authorized": True,
        "owner_sensitive": False,
        "attempt_number": 0,
        "semantic_reconciliation_accepted": True,
        "main_sha": A,
        "observed_main_sha": A,
        "open_prs": [{"number": 42, "state": "OPEN", "head_sha": B,
                     "relation": "PARTIAL", "integration_ready": True,
                     "owner_gate": False, "writer_active": False}],
        "intent": {"kind": "INTEGRATE_PR", "issue_approved": True,
                   "dependency_evidence_complete": True, "pr_number": 42, "pr_head_sha": B},
    }


class SingletonAdmissionTests(unittest.TestCase):
    def test_pr_first_candidate(self):
        self.assertEqual(evaluate(baseline())["decision"], "REUSE_EXISTING_PR")

    def test_never_launches(self):
        result = evaluate(baseline())
        self.assertFalse(result["launched"])
        self.assertFalse(result["execution_authorized"])

    def test_all_budget_and_provider_controls_required(self):
        for key in ("evidence_complete", "budget_controls_verified",
                    "cursor_on_demand_disabled", "external_billing_excluded",
                    "model_allowlisted", "subagents_disabled",
                    "launch_routes_exclusive", "provider_run_inventory_complete",
                    "semantic_reconciliation_accepted"):
            with self.subTest(key=key):
                data = baseline()
                data[key] = None
                self.assertEqual(evaluate(data)["decision"], "STOP")

    def test_duplicate_suppressed(self):
        data = baseline()
        data["prior_request_ids"] = [data["request_id"]]
        self.assertEqual(evaluate(data)["reason"], "duplicate_request")

    def test_lease_different_owner_busy(self):
        data = baseline()
        data["lease"] = {"verified_atomic": True, "state": "OWNED",
                         "owner_request_id": "other-worker"}
        self.assertEqual(evaluate(data)["decision"], "BUSY")

    def test_no_atomic_lease_cannot_pass(self):
        data = baseline()
        data["lease"]["verified_atomic"] = False
        self.assertEqual(evaluate(data)["reason"], "atomic_lease_unverified")

    def test_other_run_busy(self):
        data = baseline()
        data["active_run_ids"] = ["run-other"]
        self.assertEqual(evaluate(data)["decision"], "BUSY")

    def test_unknown_previous_launch_stops(self):
        data = baseline()
        data["ambiguous_previous_launch"] = True
        self.assertEqual(evaluate(data)["reason"], "ambiguous_prior_launch")

    def test_owner_gate(self):
        data = baseline()
        data["scope_authorized"] = False
        self.assertEqual(evaluate(data)["decision"], "OWNER_GATE")

    def test_private_security_gate(self):
        data = baseline()
        data["owner_sensitive"] = True
        self.assertEqual(evaluate(data)["decision"], "OWNER_GATE")

    def test_attempts_bounded(self):
        data = baseline()
        data["attempt_number"] = 3
        self.assertEqual(evaluate(data)["reason"], "retry_limit_or_attempt_unknown")

    def test_stale_default_sha(self):
        data = baseline()
        data["observed_main_sha"] = B
        self.assertEqual(evaluate(data)["reason"], "stale_default_sha")

    def test_invalid_pr_head(self):
        data = baseline()
        data["open_prs"][0]["head_sha"] = "bad"
        self.assertEqual(evaluate(data)["reason"], "unverifiable_pr_head")

    def test_stale_selected_pr_head(self):
        data = baseline()
        data["intent"]["pr_head_sha"] = A
        self.assertEqual(evaluate(data)["reason"], "stale_pr_head")

    def test_other_writer_busy(self):
        data = baseline()
        data["open_prs"][0]["writer_active"] = True
        self.assertEqual(evaluate(data)["decision"], "BUSY")

    def test_new_code_rejected_while_pr_ready(self):
        data = baseline()
        data["intent"] = {"kind": "NEW_CODE", "issue_approved": True,
                          "dependency_evidence_complete": True,
                          "no_overlap_verified": True}
        self.assertEqual(evaluate(data)["reason"], "integration_first_existing_pr_ready")

    def test_new_code_with_unknown_independence_owner_gate(self):
        data = baseline()
        data["open_prs"][0]["integration_ready"] = False
        data["intent"] = {"kind": "NEW_CODE", "issue_approved": True,
                          "dependency_evidence_complete": True,
                          "no_overlap_verified": True}
        self.assertEqual(evaluate(data)["decision"], "OWNER_GATE")

    def test_new_code_independent_from_blocked_pr(self):
        data = baseline()
        data["open_prs"][0]["integration_ready"] = False
        data["intent"] = {"kind": "NEW_CODE", "issue_approved": True,
                          "dependency_evidence_complete": True,
                          "no_overlap_verified": True,
                          "independent_leaf_proven": True}
        self.assertEqual(evaluate(data)["decision"], "READY_FOR_OWNER_DISPATCH")

    def test_unknown_pr_relation_blocks_everything(self):
        data = baseline()
        data["open_prs"][0]["relation"] = "INSUFFICIENT_EVIDENCE"
        self.assertEqual(evaluate(data)["reason"], "unknown_pr_semantics")

    def test_duplicate_pr_numbers_stop(self):
        data = baseline()
        data["open_prs"].append(deepcopy(data["open_prs"][0]))
        self.assertEqual(evaluate(data)["reason"], "duplicate_or_invalid_pr")

    def test_unapproved_task_owner_gate(self):
        data = baseline()
        data["intent"]["issue_approved"] = False
        self.assertEqual(evaluate(data)["decision"], "OWNER_GATE")

    def test_known_accepted_outcome_no_work(self):
        data = baseline()
        data["open_prs"][0]["relation"] = "EXACT_SAME_OUTCOME"
        data["open_prs"][0]["integration_ready"] = False
        self.assertEqual(evaluate(data)["decision"], "NO_READY_WORK")

    def test_missing_inventory_stop(self):
        data = baseline()
        data.pop("open_prs")
        self.assertEqual(evaluate(data)["reason"], "missing_open_pr_inventory")

    def test_invalid_request_identity_stop(self):
        data = baseline()
        data["request_id"] = "@cursor launch!"
        self.assertEqual(evaluate(data)["reason"], "invalid_request_id")

    def test_sensitive_billing_not_hidden_by_empty_prs(self):
        data = baseline()
        data["open_prs"] = []
        data["intent"] = {"kind": "NEW_CODE", "issue_approved": True,
                          "dependency_evidence_complete": True,
                          "no_overlap_verified": True}
        data["cursor_on_demand_disabled"] = False
        self.assertEqual(evaluate(data)["reason"], "paid_overage_possible")


if __name__ == "__main__":
    unittest.main()
