"""Synthetic concurrency and failure-path tests; NO Cursor/API calls are made."""
import copy
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from github_ref_lease import (
    Controller, GitHubRefStore, LeaseError, RefConflict, Snapshot,
    agent_id_for, check_state, fingerprint, initial_state, MAX_CONSUMED_REQUESTS, PREFIX,
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
                 "request_id": "issue-pr-284", "agent_id": agent_id_for("issue-pr-284"),
                 "consumed_request_hashes": [fingerprint("issue-pr-284")]}
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

    def test_new_issue_lease_preserves_origin_through_generated_pr(self):
        issue = "https://github.com/example/repo/issues/42"
        pr = "https://github.com/example/repo/pull/314"
        rid = "new-issue-proof-42"
        self.assertEqual(self.controller.acquire(rid, issue), "ACQUIRED")
        self.assertEqual(self.store.state["source_issue_url"], issue)
        self.assertEqual(self.store.state["pr_url"], issue)
        self.controller.transition(rid, "RESERVED", "DISPATCHING")
        self.controller.transition(rid, "DISPATCHING", "RUNNING",
                                   run_id="run-00000000-0000-0000-0000-000000000001")
        with self.assertRaises(LeaseError):
            self.controller.bind_generated_pr(rid, expected_issue_url=issue,
                                              generated_pr_url=pr)
        self.controller.transition(rid, "RUNNING", "VERIFYING")
        self.assertEqual(self.controller.bind_generated_pr(
            rid, expected_issue_url=issue, generated_pr_url=pr), "BOUND_PR")
        self.assertEqual(self.store.state["pr_url"], pr)
        self.assertEqual(self.store.state["source_issue_url"], issue)
        with self.assertRaises(LeaseError):
            self.controller.bind_generated_pr(
                rid, expected_issue_url=issue,
                generated_pr_url="https://github.com/example/repo/pull/315")

    def test_issue_lease_rejects_cross_repository_generated_pr(self):
        issue = "https://github.com/example/repo/issues/42"
        rid = "new-issue-other-repo"
        self.controller.acquire(rid, issue)
        self.controller.transition(rid, "RESERVED", "DISPATCHING")
        self.controller.transition(rid, "DISPATCHING", "RUNNING",
                                   run_id="run-00000000-0000-0000-0000-000000000001")
        self.controller.transition(rid, "RUNNING", "VERIFYING")
        with self.assertRaises(LeaseError):
            self.controller.bind_generated_pr(
                rid, expected_issue_url=issue,
                generated_pr_url="https://github.com/other/repo/pull/314")

    def test_pr_lease_never_accepts_issue_pr_rebinding(self):
        rid = "existing-pr-only"
        self.controller.acquire(rid, "https://github.com/example/repo/pull/22")
        self.controller.transition(rid, "RESERVED", "DISPATCHING")
        self.controller.transition(rid, "DISPATCHING", "RUNNING",
                                   run_id="run-00000000-0000-0000-0000-000000000001")
        self.controller.transition(rid, "RUNNING", "VERIFYING")
        with self.assertRaises(LeaseError):
            self.controller.bind_generated_pr(
                rid, expected_issue_url="https://github.com/example/repo/issues/42",
                generated_pr_url="https://github.com/example/repo/pull/314")

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

    def test_same_request_stays_consumed_after_verified_release(self):
        request = "issue-pr-284"
        self.assertEqual(self.gate.acquire(request, PR), "ACQUIRED")
        self.gate.transition(request, "RESERVED", "DISPATCHING")
        self.gate.transition(request, "DISPATCHING", "RUNNING", run_id="run-123")
        self.gate.transition(request, "RUNNING", "VERIFYING")
        self.gate.release_verified(request, provider_terminal=True,
                                   integration_accepted=True, manual_approval=True)
        self.assertEqual(Controller(self.store).acquire(request, PR), "ALREADY_CONSUMED")
        self.assertEqual(self.store.state["phase"], "IDLE")
        self.assertEqual(self.store.state["consumed_request_hashes"], [fingerprint(request)])
        self.assertNotIn(request, repr(self.store.state["consumed_request_hashes"]))

    def test_cancelled_reservation_consumes_id_but_other_can_run(self):
        request = "issue-pr-284"
        self.gate.acquire(request, PR)
        self.gate.transition(request, "RESERVED", "IDLE")
        self.assertEqual(self.gate.acquire(request, PR), "ALREADY_CONSUMED")
        self.assertEqual(self.gate.acquire("fresh-issue-285", PR), "ACQUIRED")

    def test_old_legacy_idle_state_rejected_until_explicit_migration(self):
        self.store.state = {k: v for k, v in initial_state().items()
                            if k != "consumed_request_hashes"}
        with self.assertRaisesRegex(LeaseError, "replay ledger"):
            self.gate.acquire("issue-pr-284", PR)

    def test_active_request_not_in_history_stops(self):
        self.gate.acquire("issue-pr-284", PR)
        self.store.state["consumed_request_hashes"] = []
        with self.assertRaisesRegex(LeaseError, "active request missing"):
            self.gate.acquire("different-issue-99", PR)

    def test_corrupt_and_duplicate_history_stops(self):
        for entries in (["bad"], ["a" * 64, "a" * 64], [True], ["A" * 64]):
            with self.subTest(entries=entries):
                self.store.state = {**initial_state(), "consumed_request_hashes": entries}
                with self.assertRaises(LeaseError):
                    self.gate.acquire("issue-pr-284", PR)

    def test_full_history_stops_without_mutation(self):
        initial = {**initial_state(), "consumed_request_hashes": [
            format(i, "064x") for i in range(MAX_CONSUMED_REQUESTS)
        ]}
        check_state(initial)
        self.store.state = initial
        before = self.store.read().sha
        self.assertEqual(self.gate.acquire("issue-pr-284", PR), "HISTORY_FULL")
        self.assertEqual(before, self.store.read().sha)

    def test_release_preserves_every_prior_fingerprint(self):
        a, b = "first-issue-284", "second-issue-285"
        self.gate.acquire(a, PR)
        self.gate.transition(a, "RESERVED", "IDLE")
        self.gate.acquire(b, PR)
        self.gate.transition(b, "RESERVED", "DISPATCHING")
        self.gate.transition(b, "DISPATCHING", "RUNNING", run_id="run-456")
        self.gate.transition(b, "RUNNING", "VERIFYING")
        self.gate.release_verified(b, provider_terminal=True,
                                   integration_accepted=True, manual_approval=True)
        self.assertEqual(self.store.state["consumed_request_hashes"],
                         [fingerprint(a), fingerprint(b)])
        self.assertEqual(self.gate.acquire(a, PR), "ALREADY_CONSUMED")
        self.assertEqual(self.gate.acquire(b, PR), "ALREADY_CONSUMED")

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
                 "request_id": "issue-pr-284", "agent_id": agent_id_for("issue-pr-284"),
                 "consumed_request_hashes": [fingerprint("issue-pr-284")]}
        with patch.object(api, "_call", side_effect=[{"sha": "c" * 40}, {}]) as call:
            self.assertEqual(api.advance(observed, state), "c" * 40)
        self.assertEqual(call.call_args_list[0].args[0:2], ("POST", "/git/commits"))
        self.assertEqual(call.call_args_list[0].args[2]["parents"], ["a" * 40])
        self.assertEqual(call.call_args_list[1].args[0:2], ("PATCH", "/git/refs/heads/ai-eng-cursor-lease-v1"))
        self.assertIs(call.call_args_list[1].args[2]["force"], False)

    def test_adapter_refuses_wiping_replay_history(self):
        api = GitHubRefStore("DaniilSydorenko/.github", "test-token")
        old = {**initial_state(), "revision": 4,
               "consumed_request_hashes": [fingerprint("earlier-issue-121")]}
        observed = Snapshot("a" * 40, "b" * 40, old)
        wiped = {**initial_state(), "revision": 5}
        with patch.object(api, "_call") as client, self.assertRaisesRegex(
                LeaseError, "replay ledger rollback"):
            api.advance(observed, wiped)
        client.assert_not_called()

    def test_adapter_refuses_spurious_replay_history_append(self):
        api = GitHubRefStore("DaniilSydorenko/.github", "test-token")
        observed = Snapshot("a" * 40, "b" * 40, initial_state())
        illegal = {**initial_state(), "revision": 1,
                   "consumed_request_hashes": [fingerprint("earlier-issue-121")]}
        with patch.object(api, "_call") as client, self.assertRaisesRegex(
                LeaseError, "without new owned admission"):
            api.advance(observed, illegal)
        client.assert_not_called()

    def test_adapter_refuses_prior_legacy_state_without_ledger(self):
        api = GitHubRefStore("DaniilSydorenko/.github", "test-token")
        legacy = {k: v for k, v in initial_state().items()
                  if k != "consumed_request_hashes"}
        observed = Snapshot("a" * 40, "b" * 40, legacy)
        target = {**initial_state(), "revision": 1}
        with patch.object(api, "_call") as client, self.assertRaisesRegex(
                LeaseError, "replay ledger"):
            api.advance(observed, target)
        client.assert_not_called()

    def test_adapter_conflict_does_not_retry(self):
        api = GitHubRefStore("DaniilSydorenko/.github", "test-token")
        observed = Snapshot("a" * 40, "b" * 40, initial_state())
        state = {**initial_state(), "revision": 1, "phase": "RESERVED",
                 "request_id": "issue-pr-284", "agent_id": agent_id_for("issue-pr-284"),
                 "consumed_request_hashes": [fingerprint("issue-pr-284")]}
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
