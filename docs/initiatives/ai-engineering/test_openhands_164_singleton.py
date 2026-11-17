#!/usr/bin/env python3
"""#164 offline-only three-issue singleton/replay regression.

Exercises the existing Cursor CAS state machine as a *candidate* for reuse.
This does NOT authorize or prove live OpenHands exclusivity, protected GitHub
ref permissions, or safe release after Draft PR verification.
"""
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from github_ref_lease import Controller, LeaseError
from test_github_ref_lease import MemoryGitRef

REPO = "https://github.com/DaniilSydorenko/haversine-geolocation"
ISSUES = (216, 217, 226)


class ThreeIssueSingletonTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryGitRef()

    def request(self, issue):
        return f"openhands-164-issue-{issue}"

    def url(self, issue):
        return f"{REPO}/issues/{issue}"

    def test_two_simultaneous_issues_exactly_one_wins(self):
        barrier = Barrier(2)

        def contender(issue):
            barrier.wait()
            return Controller(self.store).acquire(self.request(issue), self.url(issue))

        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(contender, 216)
            b = pool.submit(contender, 217)
            results = [a.result(), b.result()]
        self.assertEqual(results.count("ACQUIRED"), 1)
        self.assertEqual(sum(x in ("BUSY", "RACE_LOST") for x in results), 1)

    def test_restart_and_ambiguous_dispatch_block_next_issue(self):
        first = self.request(216)
        gate = Controller(self.store)
        self.assertEqual(gate.acquire(first, self.url(216)), "ACQUIRED")
        gate.transition(first, "RESERVED", "DISPATCHING")
        self.assertEqual(Controller(self.store).acquire(
            self.request(217), self.url(217)), "BUSY")
        with self.assertRaises(LeaseError):
            gate.release_verified(first, provider_terminal=False,
                                  integration_accepted=False, manual_approval=True)
        self.assertEqual(Controller(self.store).acquire(
            self.request(226), self.url(226)), "BUSY")

    def test_verified_release_does_not_replay_previous_issue(self):
        first = self.request(216)
        gate = Controller(self.store)
        self.assertEqual(gate.acquire(first, self.url(216)), "ACQUIRED")
        gate.transition(first, "RESERVED", "DISPATCHING")
        gate.transition(first, "DISPATCHING", "RUNNING", run_id="run-164-216")
        gate.transition(first, "RUNNING", "VERIFYING")
        # Simulated owner acceptance only; NOT a Draft PR evidence verifier.
        gate.release_verified(first, provider_terminal=True,
                              integration_accepted=True, manual_approval=True)
        self.assertEqual(Controller(self.store).acquire(
            first, self.url(216)), "ALREADY_CONSUMED")
        self.assertEqual(Controller(self.store).acquire(
            self.request(217), self.url(217)), "ACQUIRED")
        self.assertEqual(Controller(self.store).acquire(
            self.request(226), self.url(226)), "BUSY")


if __name__ == "__main__":
    unittest.main()
