"""Synthetic concurrency and failure-path tests; NO Cursor/API calls are made."""
import copy
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from github_ref_lease import (
    Controller, GitHubRefStore, LeaseError, RefConflict, Snapshot,
    agent_id_for, initial_state, PREFIX,
)


class MemoryGitRef:
    """Simulates GitHub non-forced fast-forward: a stale sibling cannot win."""
    def __init__(self):
        self._mutex = threading.Lock()
        self.sha = "a" * 40
        self.state = initial_state()
        self.tree = "b" * 40
        self.fail_on_advance = False

    def read(self):
        with self._mutex:
            return Snapshot(self.sha, self.tree, copy.deepcopy(self.state))

    def advance(self, observed, new_state):
        with self._mutex:
            if self.fail_on_advance:
                raise LeaseError("provider outage")
            if self.sha != observed.sha:
                raise RefConflict("GitHub rejected non-fast-forward")
            self.sha = format(int(self.sha, 16) + 1, "040x")
            self.state = copy.deepcopy(new_state)
            return self.sha


PR = "https://github.com/DaniilSydorenko/listing-kit/pull/284"


class LeaseTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryGitRef()
        self.gate = Controller(self.store)

    def test_only_one_of_two_simultaneous_contenders_can_acquire(self):
        barrier = threading.Barrier(2)
        answers = []

        def work(key):
            barrier.wait()
            return self.gate.acquire(key, PR)

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(work, "first-issue-284")
            f2 = pool.submit(work, "second-issue-284")
            answers = [f1.result(), f2.result()]
        self.assertEqual(answers.count("ACQUIRED"), 1)
        self.assertEqual(len([x for x in answers if x in ("BUSY", "RACE_LOST")]), 1)

    def test_same_request_replay_cannot_start_another_agent(self):
        self.assertEqual(self.gate.acquire("issue-pr-284", PR), "ACQUIRED")
        self.assertEqual(self.gate.acquire("issue-pr-284", PR), "ALREADY_OWNED")
        self.assertEqual(self.store.state["revision"], 1)

    def test_lease_is_persistent_between_controller_instances(self):
        self.gate.acquire("issue-pr-284", PR)
        fresh = Controller(self.store)
        self.assertEqual(fresh.acquire("other-task-99", PR), "BUSY")

    def test_cas_race_rejects_second_write(self):
        s1 = self.store.read()
        s2 = self.store.read()
        owned = {**initial_state(), "revision": 1, "phase": "RESERVED",
                 "request_id": "issue-pr-284", "agent_id": agent_id_for("issue-pr-284")}
        self.store.advance(s1, owned)
        with self.assertRaises(RefConflict):
            self.store.advance(s2, owned)

    def test_acquire_needs_valid_request(self):
        for value in ("@cursor", "oops", "bad space", "../traverse"):
            with self.subTest(value=value), self.assertRaises(LeaseError):
                self.gate.acquire(value, PR)

    def test_acquire_only_scoped_pr(self):
        for value in ("https://evil.example/pr/12", "https://github.com/x/y/issues/12",
                      "https://github.com/x/y/pull/12?@cursor", "http://github.com/x/y/pull/12"):
            with self.subTest(value=value), self.assertRaises(LeaseError):
                self.gate.acquire("issue-pr-284", value)

    def test_acquire_outage_must_fail_closed(self):
        self.store.fail_on_advance = True
        with self.assertRaises(LeaseError):
            self.gate.acquire("issue-pr-284", PR)

    def test_dispatch_phase_is_recorded_before_external_api_call(self):
        self.gate.acquire("issue-pr-284", PR)
        self.assertEqual(self.gate.transition("issue-pr-284", "RESERVED", "DISPATCHING"), "DISPATCHING")
        self.assertEqual(self.gate.acquire("issue-pr-284", PR), "ALREADY_OWNED")
        self.assertEqual(self.gate.acquire("other-task-99", PR), "BUSY")

    def test_ambiguous_launch_blocks_new_run(self):
        self.gate.acquire("issue-pr-284", PR)
        self.gate.transition("issue-pr-284", "RESERVED", "DISPATCHING")
        self.assertEqual(Controller(self.store).acquire("other-task-99", PR), "BUSY")
        with self.assertRaises(LeaseError):
            self.gate.release_verified("issue-pr-284", provider_terminal=False,
                                       integration_accepted=False, manual_approval=True)

    def test_run_identity_required(self):
        self.gate.acquire("issue-pr-284", PR)
        self.gate.transition("issue-pr-284", "RESERVED", "DISPATCHING")
        with self.assertRaises(LeaseError):
            self.gate.transition("issue-pr-284", "DISPATCHING", "RUNNING", run_id="unverified")
        self.assertEqual(self.store.state["phase"], "DISPATCHING")

    def test_wrong_owner_cannot_transition(self):
        self.gate.acquire("issue-pr-284", PR)
        with self.assertRaises(LeaseError):
            self.gate.transition("other-task-99", "RESERVED", "DISPATCHING")

    def test_wrong_prior_phase_cannot_advance(self):
        self.gate.acquire("issue-pr-284", PR)
        with self.assertRaises(LeaseError):
            self.gate.transition("issue-pr-284", "DISPATCHING", "RUNNING", run_id="run-123")

    def test_no_direct_release_from_running(self):
        self.gate.acquire("issue-pr-284", PR)
        self.gate.transition("issue-pr-284", "RESERVED", "DISPATCHING")
        self.gate.transition("issue-pr-284", "DISPATCHING", "RUNNING", run_id="run-123")
        with self.assertRaises(LeaseError):
            self.gate.release_verified("issue-pr-284", provider_terminal=True,
                                       integration_accepted=True, manual_approval=True)

    def test_no_release_without_all_three_proofs(self):
        self.gate.acquire("issue-pr-284", PR)
        self.gate.transition("issue-pr-284", "RESERVED", "DISPATCHING")
        self.gate.transition("issue-pr-284", "DISPATCHING", "RUNNING", run_id="run-123")
        self.gate.transition("issue-pr-284", "RUNNING", "VERIFYING")
        for args in ((False, True, True), (True, False, True), (True, True, False)):
            with self.subTest(args=args), self.assertRaises(LeaseError):
                self.gate.release_verified("issue-pr-284", provider_terminal=args[0],
                                           integration_accepted=args[1], manual_approval=args[2])
        self.assertEqual(self.store.state["phase"], "VERIFYING")

    def test_release_after_owner_proofs(self):
        self.gate.acquire("issue-pr-284", PR)
        self.gate.transition("issue-pr-284", "RESERVED", "DISPATCHING")
        self.gate.transition("issue-pr-284", "DISPATCHING", "RUNNING", run_id="run-123")
        self.gate.transition("issue-pr-284", "RUNNING", "VERIFYING")
        self.assertEqual(self.gate.release_verified("issue-pr-284", provider_terminal=True,
                                                    integration_accepted=True,
                                                    manual_approval=True), "RELEASED")
        self.assertEqual(self.store.state["phase"], "IDLE")
        self.assertEqual(self.gate.acquire("other-task-99", PR), "ACQUIRED")

    def test_illegal_state_transition_rejected(self):
        self.gate.acquire("issue-pr-284", PR)
        with self.assertRaises(LeaseError):
            self.gate.transition("issue-pr-284", "RESERVED", "RUNNING", run_id="run-123")

    def test_corrupt_or_unknown_state_blocks(self):
        self.store.state = {"version": 1, "revision": 0, "phase": "oops"}
        with self.assertRaises(LeaseError):
            self.gate.acquire("issue-pr-284", PR)

    def test_deterministic_idempotent_provider_identity(self):
        x = agent_id_for("issue-pr-284")
        self.assertEqual(x, agent_id_for("issue-pr-284"))
        self.assertNotEqual(x, agent_id_for("other-task-99"))
        self.assertTrue(x.startswith("bc-"))


class GithubAPIAdapterTests(unittest.TestCase):
    def test_github_uses_nonforced_update(self):
        api = GitHubRefStore("DaniilSydorenko/.github", "test-token")
        observed = Snapshot("a" * 40, "b" * 40, initial_state())
        state = {**initial_state(), "revision": 1, "phase": "RESERVED",
                 "request_id": "issue-pr-284", "agent_id": agent_id_for("issue-pr-284")}
        with patch.object(api, "_call", side_effect=[{"sha": "c" * 40}, {}]) as call:
            self.assertEqual(api.advance(observed, state), "c" * 40)
        self.assertEqual(call.call_args_list[0].args[0:2], ("POST", "/git/commits"))
        self.assertEqual(call.call_args_list[0].args[2]["parents"], ["a" * 40])
        self.assertEqual(call.call_args_list[1].args[0:2], ("PATCH", "/git/refs/heads/ai-eng-cursor-lease-v1"))
        self.assertIs(call.call_args_list[1].args[2]["force"], False)

    def test_adapter_conflict_does_not_retry(self):
        api = GitHubRefStore("DaniilSydorenko/.github", "test-token")
        observed = Snapshot("a" * 40, "b" * 40, initial_state())
        state = {**initial_state(), "revision": 1, "phase": "RESERVED",
                 "request_id": "issue-pr-284", "agent_id": agent_id_for("issue-pr-284")}
        with patch.object(api, "_call", side_effect=[{"sha": "c" * 40}, RefConflict("raced")]) as call:
            with self.assertRaises(RefConflict):
                api.advance(observed, state)
        self.assertEqual(call.call_count, 2)

    def test_adapter_read_ref_and_git_commit(self):
        api = GitHubRefStore("DaniilSydorenko/.github", "test-token")
        snap = initial_state()
        with patch.object(api, "_call", side_effect=[
            {"object": {"sha": "a" * 40}},
            {"message": PREFIX + json.dumps(snap), "tree": {"sha": "b" * 40}},
        ]) as call:
            self.assertEqual(api.read().state, snap)
        self.assertEqual(call.call_count, 2)

    def test_adapter_ref_missing_stops(self):
        api = GitHubRefStore("DaniilSydorenko/.github", "test-token")
        with patch.object(api, "_call", side_effect=LeaseError("GitHub 404")):
            with self.assertRaises(LeaseError):
                api.read()


if __name__ == "__main__":
    unittest.main()
