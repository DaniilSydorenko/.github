"""Full two-Issue transaction smoke without network, paid models or GH writes.

One accepted PR -> one approved Issue -> one synthetic Cursor run -> owned PR
-> exact-head checks -> owner acceptance -> durable lease release -> next Issue.
THIS IS TEST EVIDENCE ONLY, not an authorized production dispatch workflow.
"""
from copy import deepcopy
from unittest import TestCase, main
from unittest.mock import patch

from execution_outcome import verify_execution
from github_ref_lease import Controller, LeaseError
from managed_cursor_launch import launch_single_approved_issue
from sequential_handoff import preview_next_after_merge
from test_github_ref_lease import MemoryGitRef
from test_managed_cursor_issue_launch import approved_handoff, snapshot, approval
from test_managed_cursor_launch import ReaderStub

REPO = "example/test"
A, B, C = "a"*40, "b"*40, "c"*40
PATH = "src/feature.py"


class TwoRunsStub:
    def __init__(self):
        self.created = []

    def create(self, payload):
        self.created.append(payload)
        number = len(self.created)
        return {
            "agent_id": payload["agentId"],
            "run_id": "run-00000000-0000-0000-0000-" + f"{number:012d}"
        }


def next_issue_after_accepted_42():
    data = snapshot()
    task = {
        "number": 43, "order": 3, "state": "open", "accepted": False,
        "owner_approved": True, "owner_gate": False, "scope": "ui_low_risk",
        "allowed_paths": [PATH],
        "dependencies": [{"number": 42, "status": "accepted"}],
    }
    data["handoff"]["previous"].update(pr_number=312, head_sha=B, merge_sha=C,
                                      merge_on_default_verified=True,
                                      ci="SUCCESS", secret_scan="SUCCESS",
                                      owner_visual_acceptance="accepted")
    data["handoff"]["queue"][1].update(state="closed", accepted=True)
    data["handoff"]["queue"].append(task)
    scoped = data["preview"]
    scoped["collector"]["observed_facts"]["issue_number"] = 43
    scoped["observed"]["issue_number"] = 43
    scoped["semantic"]["issue_number"] = 43
    scoped["semantic"]["issue_url"] = f"https://github.com/{REPO}/issues/43"
    scoped["task"]["issue"] = f"https://github.com/{REPO}/issues/43"
    return data


def accepted_evidence(store, *, issue_number, number, result, ci="success",
                      accepted=True, device="not_required"):
    url = f"https://github.com/{REPO}/pull/{number}"
    return {
        "schema_version": 1,
        "task": {
            "repository": REPO, "issue_number": issue_number, "pr_number": number,
            "pr_url": url, "request_id": store.state["request_id"],
            "owner_authority": "verified", "scope_authority": "verified",
            "allowed_paths": [PATH], "required_checks": ["CI", "Secret Scan"],
        },
        "lease": {**deepcopy(store.state),
                  "observed_revision": store.state["revision"]},
        "provider": {
            "agent_id": result["agent_id"], "run_id": result["run_id"],
            "run": {"id": result["run_id"], "agentId": result["agent_id"],
                    "status": "FINISHED"},
            "observation_complete": True, "other_active_run": False,
        },
        "pr": {
            "number": number, "url": url, "state": "closed", "merged": True,
            "head_sha": B, "observed_head_sha": B,
            "base_sha": A, "observed_base_sha": A,
            "merge_sha": C, "merged_into_default_proven": True,
            "changed_paths": [PATH], "changed_paths_complete": True,
        },
        "checks": [
            {"name": "CI", "head_sha": B, "conclusion": ci, "observed": True},
            {"name": "Secret Scan", "head_sha": B,
             "conclusion": "success", "observed": True},
        ],
        "attempts": {"initial_run_verified": True, "corrections": [],
                     "failure_evidence_verified": False},
        "acceptance": {
            "issue_criteria": "accepted" if accepted else "pending",
            "owner_merge": "approved", "deployment": "not_required",
            "device": device,
        },
    }


class TwoIssueCycleTests(TestCase):
    def setUp(self):
        self.store = MemoryGitRef()
        self.lease = Controller(self.store)
        self.reader = ReaderStub()
        self.provider = TwoRunsStub()

    def dispatch(self, data, *, permit=None):
        recommendation = preview_next_after_merge(data["handoff"])
        rid = recommendation["proposed_request_id"]
        self.assertEqual(recommendation["action"], "READY_FOR_OWNER_DISPATCH")
        pr = permit or approval()
        pr.update(request_id=rid, proposed_request_id=rid,
                  repository=REPO, issue_number=recommendation["next_issue_number"],
                  head_sha=A)
        return launch_single_approved_issue(
            request_id=rid, bundle=data, permit=pr,
            controller=self.lease, cursor_reader=self.reader,
            cursor_create=self.provider,
        )

    def finalize(self, issue, pr_number, launched, *, accepted=True, ci="success"):
        rid = self.store.state["request_id"]
        self.assertEqual(self.store.state["phase"], "RUNNING")
        self.lease.transition(rid, "RUNNING", "VERIFYING")
        self.lease.bind_generated_pr(
            rid, expected_issue_url=f"https://github.com/{REPO}/issues/{issue}",
            generated_pr_url=f"https://github.com/{REPO}/pull/{pr_number}",
        )
        evidence = accepted_evidence(
            self.store, issue_number=issue, number=pr_number, result=launched,
            accepted=accepted, ci=ci,
        )
        checked = verify_execution(evidence)
        if checked["status"] == "ACCEPTED_OBSERVED":
            self.assertFalse(checked["release_lease_authorized"])
            # Represents a separately trusted owner action after independently
            # verifying all required GH/provider facts. Not production proof.
            self.lease.release_verified(
                rid, provider_terminal=True, integration_accepted=True,
                manual_approval=True,
            )
        return checked

    def test_two_issues_sequentially_and_no_duplicate_model_launch(self):
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True), \
             patch("managed_cursor_launch._trusted_lease_ref_audit",
                   return_value=True):
            issue42 = self.dispatch(snapshot())
            self.assertEqual(issue42["state"], "STARTED")
            self.assertEqual(len(self.provider.created), 1)
            first_rid = self.store.state["request_id"]
            first_proposal = self.store.state["source_issue_url"]

            # An event repeated while first agent owns the lease cannot POST.
            duplicate = self.dispatch(snapshot())
            self.assertEqual(duplicate["state"], "BUSY")
            self.assertEqual(len(self.provider.created), 1)
            self.assertEqual(self.store.state["source_issue_url"], first_proposal)

            verified = self.finalize(42, 312, issue42)
            self.assertEqual(verified["status"], "ACCEPTED_OBSERVED")
            self.assertEqual(self.store.state["phase"], "IDLE")
            self.assertEqual(len(self.store.state["consumed_request_hashes"]), 1)

            # Replayed old event cannot create the first agent again.
            replay = self.dispatch(snapshot())
            self.assertEqual(replay["reason"], "lease_already_consumed")
            self.assertEqual(len(self.provider.created), 1)

            next_task = next_issue_after_accepted_42()
            issue43 = self.dispatch(next_task)
            self.assertEqual(issue43["state"], "STARTED")
            self.assertNotEqual(issue42["agent_id"], issue43["agent_id"])
            self.assertEqual(len(self.provider.created), 2)
            self.assertEqual(len(self.store.state["consumed_request_hashes"]), 2)
            self.assertNotEqual(first_rid, self.store.state["request_id"])
            self.assertEqual(issue43["work_url"],
                             f"https://github.com/{REPO}/issues/43")
            self.assertFalse(issue43["automatic_merge"])

            second = self.finalize(43, 313, issue43)
            self.assertEqual(second["status"], "ACCEPTED_OBSERVED")
            self.assertEqual(self.store.state["phase"], "IDLE")
            self.assertEqual(len(self.store.state["consumed_request_hashes"]), 2)

    def test_green_ci_with_unaccepted_owner_blocks_second_agent(self):
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True), \
             patch("managed_cursor_launch._trusted_lease_ref_audit",
                   return_value=True):
            first = self.dispatch(snapshot())
            checked = self.finalize(42, 312, first, accepted=False)
            # The production terminal verifier deliberately returns STOP
            # for an already-merged PR whose owner acceptance is unproven.
            # Do not weaken that fail-closed guard to make this test green.
            self.assertEqual(checked["status"], "STOP")
            self.assertEqual(checked["reason"],
                             "merged_pr_without_authenticated_acceptance")
            self.assertEqual(self.store.state["phase"], "VERIFYING")
            # A fresh, separately approved second issue cannot steal the slot.
            next_task = next_issue_after_accepted_42()
            second = self.dispatch(next_task)
            self.assertEqual(second["state"], "BUSY")
            self.assertEqual(len(self.provider.created), 1)

    def test_failed_exact_head_ci_keeps_lease_for_correction_review(self):
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True), \
             patch("managed_cursor_launch._trusted_lease_ref_audit",
                   return_value=True):
            first = self.dispatch(snapshot())
            checked = self.finalize(42, 312, first, ci="failure")
            self.assertEqual(checked["status"], "STOP")
            self.assertEqual(self.store.state["phase"], "VERIFYING")
            self.assertEqual(len(self.provider.created), 1)

    def test_real_dispatch_stays_killed_even_when_simulated_preconditions_pass(self):
        args = snapshot()
        result = self.dispatch(args)
        self.assertEqual(result["state"], "DISABLED")
        self.assertEqual(len(self.provider.created), 0)
        self.assertEqual(self.store.state["phase"], "IDLE")


if __name__ == "__main__":
    main()
