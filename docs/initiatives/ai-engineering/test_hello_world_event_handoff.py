"""SIMULATION ONLY: PR_A_ACCEPTED event bridge → stubbed Issue B dispatch."""
from copy import deepcopy
from unittest import TestCase, main
from unittest.mock import patch

from github_ref_lease import Controller
from hello_world_event_handoff import (
    HelloWorldEventSimulator,
    SyntheticAcceptEvent,
    handoff_after_issue_a_accepted,
)
from test_github_ref_lease import MemoryGitRef
from test_managed_cursor_launch import ReaderStub
from test_two_issue_cycle import TwoRunsStub


def accept_event(**overrides):
    base = SyntheticAcceptEvent(
        kind="PR_A_ACCEPTED",
        event_id="accept-a-312-v1",
        pr_number=312,
        head_sha="b" * 40,
        merge_sha="c" * 40,
        owner_accepted=True,
        ci_conclusion="success",
    )
    if overrides:
        return SyntheticAcceptEvent(**{**base.__dict__, **overrides})
    return base


class HelloWorldEventHandoffTests(TestCase):
    def setUp(self):
        self.store = MemoryGitRef()
        self.lease = Controller(self.store)
        self.reader = ReaderStub()
        self.provider = TwoRunsStub()
        self.sim = HelloWorldEventSimulator(
            controller=self.lease,
            cursor_reader=self.reader,
            cursor_create=self.provider,
        )
        self.pilot = patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True)
        self.audit = patch(
            "managed_cursor_launch._trusted_lease_ref_audit", return_value=True
        )
        self.pilot.start()
        self.audit.start()
        self.addCleanup(self.pilot.stop)
        self.addCleanup(self.audit.stop)

    def test_full_cycle_accept_a_dispatches_b_via_event_only(self):
        issue_a = self.sim.start_issue_a()
        self.assertEqual(issue_a["state"], "STARTED")
        self.assertEqual(len(self.provider.created), 1)

        self.sim.wait_for_owner_accept()
        checked_a = self.sim.finalize_issue_a(issue_a)
        self.assertEqual(checked_a["status"], "ACCEPTED_OBSERVED")
        self.assertEqual(self.store.state["phase"], "IDLE")

        event = accept_event()
        issue_b = self.sim.handle_pr_a_accepted(event)
        self.assertEqual(issue_b["state"], "STARTED")
        self.assertTrue(self.sim.issue_b_via_event)
        self.assertEqual(len(self.provider.created), 2)
        self.assertNotEqual(issue_a["agent_id"], issue_b["agent_id"])

        replay = self.sim.handle_pr_a_accepted(event)
        self.assertEqual(replay["state"], "IGNORED")
        self.assertEqual(replay["reason"], "replay_suppressed")
        self.assertEqual(len(self.provider.created), 2)

        checked_b = self.sim.finalize_issue_b(issue_b)
        self.assertEqual(checked_b["status"], "ACCEPTED_OBSERVED")

        self.assertEqual(
            self.sim.trace,
            [
                "START",
                "PR",
                "WAIT_ACCEPT",
                "ACCEPT",
                "LEASE_RELEASE",
                "NEXT",
                "ACCEPT",
                "LEASE_RELEASE",
                "STOP",
            ],
        )

    def test_replay_before_dispatch_still_single_agent_cap(self):
        issue_a = self.sim.start_issue_a()
        self.sim.finalize_issue_a(issue_a)
        event = accept_event()
        first = self.sim.handle_pr_a_accepted(event)
        second = self.sim.handle_pr_a_accepted(event)
        self.assertEqual(first["state"], "STARTED")
        self.assertEqual(second["state"], "IGNORED")
        self.assertEqual(len(self.provider.created), 2)

    def test_owner_gate_blocks_event_dispatch(self):
        issue_a = self.sim.start_issue_a()
        self.sim.finalize_issue_a(issue_a, accepted=False)
        self.assertEqual(self.store.state["phase"], "VERIFYING")
        blocked = self.sim.handle_pr_a_accepted(accept_event())
        self.assertEqual(blocked["state"], "BUSY")
        self.assertEqual(len(self.provider.created), 1)

    def test_failed_ci_on_finalize_blocks_release_and_event(self):
        issue_a = self.sim.start_issue_a()
        checked = self.sim.finalize_issue_a(issue_a, ci="failure")
        self.assertEqual(checked["status"], "STOP")
        blocked = self.sim.handle_pr_a_accepted(accept_event())
        self.assertEqual(blocked["state"], "BUSY")
        self.assertEqual(len(self.provider.created), 1)

    def test_event_ci_failure_fail_closed(self):
        issue_a = self.sim.start_issue_a()
        self.sim.finalize_issue_a(issue_a)
        bad = self.sim.handle_pr_a_accepted(
            accept_event(event_id="accept-a-bad-ci", ci_conclusion="failure")
        )
        self.assertEqual(bad["state"], "STOP")
        self.assertEqual(bad["reason"], "exact_head_ci_not_green")
        self.assertEqual(len(self.provider.created), 1)

    def test_occupied_lease_blocks_event(self):
        issue_a = self.sim.start_issue_a()
        self.assertEqual(self.store.state["phase"], "RUNNING")
        busy = self.sim.handle_pr_a_accepted(accept_event())
        self.assertEqual(busy["state"], "BUSY")
        self.assertEqual(len(self.provider.created), 1)

    def test_unknown_event_and_stale_sha_fail_closed(self):
        issue_a = self.sim.start_issue_a()
        self.sim.finalize_issue_a(issue_a)
        unknown = self.sim.handle_pr_a_accepted(
            accept_event(kind="PR_MERGED_UNKNOWN", event_id="x1")
        )
        self.assertEqual(unknown["state"], "STOP")
        self.assertEqual(unknown["reason"], "unknown_event")

        stale = self.sim.handle_pr_a_accepted(
            accept_event(event_id="x2", merge_sha="d" * 40)
        )
        self.assertEqual(stale["state"], "STOP")
        self.assertEqual(stale["reason"], "stale_or_wrong_sha")
        self.assertEqual(len(self.provider.created), 1)

    def test_no_third_issue_after_queue_exhausted(self):
        issue_a = self.sim.start_issue_a()
        self.sim.finalize_issue_a(issue_a)
        self.sim.handle_pr_a_accepted(accept_event())
        issue_b_launch = self.sim._last_launch
        self.assertIsNotNone(issue_b_launch)
        self.sim.finalize_issue_b(issue_b_launch)
        self.assertEqual(len(self.provider.created), 2)
        # Handoff after B would need another issue; simulator must not invent one.
        post_b = handoff_after_issue_a_accepted()
        post_b["handoff"]["queue"][2]["state"] = "closed"
        post_b["handoff"]["queue"][2]["accepted"] = True
        sim2 = HelloWorldEventSimulator(
            controller=self.lease,
            cursor_reader=self.reader,
            cursor_create=self.provider,
            bundle=post_b,
        )
        sim2.bundle = deepcopy(post_b)
        third = sim2.handle_pr_a_accepted(
            accept_event(event_id="accept-replay-third")
        )
        self.assertIn(third["state"], ("STOP", "IGNORED", "BUSY"))
        self.assertEqual(len(self.provider.created), 2)


if __name__ == "__main__":
    main()
