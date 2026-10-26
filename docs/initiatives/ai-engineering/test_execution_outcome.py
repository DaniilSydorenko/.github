"""No-provider/no-network regression suite for terminal outcome verification."""
import copy
import unittest

from execution_outcome import verify_execution

A, B, C = "a" * 40, "b" * 40, "c" * 40
AGENT = "bc-00000000-0000-0000-0000-000000000001"
RUN = "run-00000000-0000-0000-0000-000000000001"
RUN2 = "run-00000000-0000-0000-0000-000000000002"
RUN3 = "run-00000000-0000-0000-0000-000000000003"
REPO = "example/example-app"
URL = f"https://github.com/{REPO}/pull/19"


def fixture():
    return {
        "schema_version": 1,
        "task": {"repository": REPO, "issue_number": 18, "pr_number": 19,
                 "pr_url": URL, "request_id": "task-18-pr-19",
                 "owner_authority": "verified", "scope_authority": "verified",
                 "allowed_paths": ["src/file.ts", "src/component.tsx"],
                 "required_checks": ["CI", "Secret Scan"]},
        "lease": {"phase": "VERIFYING", "revision": 7, "observed_revision": 7,
                  "request_id": "task-18-pr-19", "pr_url": URL,
                  "agent_id": AGENT, "run_id": RUN},
        "provider": {"agent_id": AGENT, "run_id": RUN,
                     "run": {"agentId": AGENT, "id": RUN, "status": "FINISHED"},
                     "observation_complete": True, "other_active_run": False},
        "pr": {"number": 19, "url": URL, "state": "open", "merged": False,
               "head_sha": A, "observed_head_sha": A,
               "base_sha": B, "observed_base_sha": B,
               "changed_paths_complete": True,
               "changed_paths": ["src/file.ts"]},
        "checks": [{"name": "CI", "head_sha": A, "conclusion": "success",
                    "observed": True},
                   {"name": "Secret Scan", "head_sha": A, "conclusion": "success",
                    "observed": True}],
        "attempts": {"initial_run_verified": True, "corrections": [],
                     "failure_evidence_verified": False},
        "acceptance": {"issue_criteria": "pending",
                       "owner_merge": "pending",
                       "deployment": "pending", "device": "pending"}
    }


def accepted(s):
    s["pr"].update(state="closed", merged=True, merge_sha=C,
                   merged_into_default_proven=True)
    s["acceptance"].update(issue_criteria="accepted", owner_merge="approved",
                           deployment="accepted", device="accepted")
    return s


class OutcomeTests(unittest.TestCase):
    def verdict(self, s, action):
        res = verify_execution(s)
        self.assertEqual(res["status"], action, res)
        self.assertIs(res["advisory_only"], True)
        self.assertIs(res["provider_called"], False)
        self.assertIs(res["new_model_invocation_authorized"], False)
        self.assertIs(res["next_issue_authorized"], False)
        self.assertIs(res["release_lease_authorized"], False)
        self.assertIs(res["automatic_merge"], False)
        self.assertEqual(res["model_runs_started"], 0)
        self.assertEqual(res["charged_cost"], "UNKNOWN")
        return res

    def test_still_running_waits(self):
        s = fixture()
        s["provider"]["run"]["status"] = "RUNNING"
        s["lease"]["phase"] = "RUNNING"
        self.verdict(s, "WAIT_RUN")

    def test_terminal_requires_verifying_lease_transition(self):
        s = fixture()
        s["lease"]["phase"] = "RUNNING"
        self.verdict(s, "WAIT_RUN")

    def test_verifying_lease_with_live_agent_fails_closed(self):
        s = fixture()
        s["provider"]["run"]["status"] = "RUNNING"
        self.verdict(s, "STOP")

    def test_unknown_run_state_stops(self):
        s = fixture()
        s["provider"]["run"]["status"] = "new-provider-status"
        self.verdict(s, "STOP")

    def test_provider_failed_cancelled_expired_cannot_proceed(self):
        for status in ("ERROR", "CANCELLED", "EXPIRED"):
            with self.subTest(status=status):
                s = fixture()
                s["provider"]["run"]["status"] = status
                self.verdict(s, "STOP")

    def test_mismatching_lease_owner_stops(self):
        s = fixture()
        s["lease"]["request_id"] = "different-request-id"
        self.verdict(s, "STOP")

    def test_mismatching_provider_run_stops(self):
        s = fixture()
        s["provider"]["run"]["id"] = RUN2
        self.verdict(s, "STOP")

    def test_other_active_provider_run_stops(self):
        s = fixture()
        s["provider"]["other_active_run"] = True
        self.verdict(s, "STOP")

    def test_unknown_global_cursor_scope_stops(self):
        s = fixture()
        s["provider"]["observation_complete"] = False
        self.verdict(s, "STOP")

    def test_owner_or_scope_absent_stops(self):
        for key in ("owner_authority", "scope_authority"):
            s = fixture()
            s["task"][key] = "unknown"
            self.verdict(s, "STOP")

    def test_stale_lease_revision_stops(self):
        s = fixture()
        s["lease"]["observed_revision"] = 6
        self.verdict(s, "STOP")

    def test_stale_head_stops(self):
        s = fixture()
        s["pr"]["observed_head_sha"] = C
        self.verdict(s, "STOP")

    def test_stale_pr_base_stops(self):
        s = fixture()
        s["pr"]["observed_base_sha"] = C
        self.verdict(s, "STOP")

    def test_out_of_scope_change_stops(self):
        s = fixture()
        s["pr"]["changed_paths"].append("secrets/prod.env")
        self.verdict(s, "STOP")

    def test_traversal_path_stops(self):
        s = fixture()
        s["task"]["allowed_paths"] = ["../secrets"]
        self.verdict(s, "STOP")

    def test_ci_pending_waits(self):
        s = fixture()
        s["checks"][0]["conclusion"] = "in_progress"
        self.verdict(s, "WAIT_CI")

    def test_missing_required_ci_waits(self):
        s = fixture()
        s["checks"].pop()
        self.verdict(s, "WAIT_CI")

    def test_stale_check_head_stops(self):
        s = fixture()
        s["checks"][0]["head_sha"] = C
        self.verdict(s, "STOP")

    def test_duplicate_checks_stops(self):
        s = fixture()
        s["checks"].append(copy.deepcopy(s["checks"][0]))
        self.verdict(s, "STOP")

    def test_failed_checks_need_diagnostic(self):
        s = fixture()
        s["checks"][0]["conclusion"] = "failure"
        self.verdict(s, "STOP")

    def test_failed_checks_can_propose_one_correction_only(self):
        s = fixture()
        s["checks"][0]["conclusion"] = "failure"
        s["attempts"]["failure_evidence_verified"] = True
        r = self.verdict(s, "CORRECTION_REVIEW")
        self.assertEqual(r["corrections_remaining"], 2)

    def test_one_prior_correction_leaves_one(self):
        s = fixture()
        s["checks"][0]["conclusion"] = "failure"
        s["attempts"]["failure_evidence_verified"] = True
        s["attempts"]["corrections"] = [{
            "index": 1, "failure_head": B,
            "evidence_ref": f"https://github.com/{REPO}/pull/19",
            "run_id": RUN2
        }]
        r = self.verdict(s, "CORRECTION_REVIEW")
        self.assertEqual(r["corrections_remaining"], 1)

    def test_two_prior_corrections_stop_any_model_retry(self):
        s = fixture()
        s["checks"][0]["conclusion"] = "failure"
        s["attempts"]["failure_evidence_verified"] = True
        s["attempts"]["corrections"] = [
            {"index": 1, "failure_head": B,
             "evidence_ref": f"https://github.com/{REPO}/pull/19", "run_id": RUN2},
            {"index": 2, "failure_head": A,
             "evidence_ref": f"https://github.com/{REPO}/pull/19", "run_id": RUN3},
        ]
        r = self.verdict(s, "STOP")
        self.assertEqual(r["corrections_remaining"], 0)

    def test_duplicate_correction_run_stops(self):
        s = fixture()
        s["attempts"]["corrections"] = [
            {"index": 1, "failure_head": B,
             "evidence_ref": f"https://github.com/{REPO}/pull/19", "run_id": RUN},
        ]
        self.verdict(s, "STOP")

    def test_three_prior_corrections_hard_stop(self):
        s = fixture()
        s["attempts"]["corrections"] = [{
            "index": i, "failure_head": B,
            "evidence_ref": f"https://github.com/{REPO}/pull/19",
            "run_id": f"run-{i:08x}-0000-0000-0000-000000000001",
        } for i in (1, 2, 3)]
        self.verdict(s, "STOP")

    def test_initial_run_provenance_required(self):
        s = fixture()
        s["attempts"]["initial_run_verified"] = None
        self.verdict(s, "STOP")

    def test_green_ci_still_owner_gate(self):
        self.verdict(fixture(), "OWNER_GATE")

    def test_green_ci_issue_accepted_still_merge_gate(self):
        s = fixture()
        s["acceptance"]["issue_criteria"] = "accepted"
        self.verdict(s, "OWNER_GATE")

    def test_closed_unmerged_is_never_accepted(self):
        s = fixture()
        s["pr"]["state"] = "closed"
        self.verdict(s, "STOP")

    def test_merged_requires_owner_approval(self):
        s = accepted(fixture())
        s["acceptance"]["owner_merge"] = "unknown"
        self.verdict(s, "STOP")

    def test_merged_requires_main_proof(self):
        s = accepted(fixture())
        s["pr"]["merged_into_default_proven"] = False
        self.verdict(s, "STOP")

    def test_merge_with_device_pending_still_gate(self):
        s = accepted(fixture())
        s["acceptance"]["device"] = "pending"
        self.verdict(s, "OWNER_GATE")

    def test_merge_with_deployment_pending_still_gate(self):
        s = accepted(fixture())
        s["acceptance"]["deployment"] = "pending"
        self.verdict(s, "OWNER_GATE")

    def test_real_completed_and_accepted_is_only_observation(self):
        s = accepted(fixture())
        r = self.verdict(s, "ACCEPTED_OBSERVED")
        self.assertFalse(r["next_issue_authorized"])
        self.assertFalse(r["release_lease_authorized"])

    def test_missing_document_no_trust(self):
        self.verdict({"schema_version": 1}, "STOP")

    def test_bad_schema_no_trust(self):
        self.verdict({"schema_version": 99}, "STOP")

    def test_wrong_related_pr_url_no_cross_repo(self):
        s = fixture()
        s["task"]["pr_url"] = "https://github.com/other/repo/pull/19"
        self.verdict(s, "STOP")

    def test_missing_check_observation_is_not_green(self):
        s = fixture()
        s["checks"][0]["observed"] = False
        self.verdict(s, "STOP")

    def test_unknown_billing_not_silently_zero(self):
        self.assertEqual(self.verdict(fixture(), "OWNER_GATE")["charged_cost"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
