"""Exact-head CI evidence must not false-PASS."""
from __future__ import annotations

import unittest

from openhands_164_ci_evidence import exact_head_ci_from_check_runs
from openhands_164_vertical_integration import CiEvidence


class CiEvidenceTests(unittest.TestCase):
    def test_empty_checks_pending_not_success(self):
        pr = {"head": {"sha": "a" * 40}}
        runs = {"check_runs": []}

        def transport(method, url, token):
            return pr if "/pulls/" in url else runs

        ev, err = exact_head_ci_from_check_runs(1, transport=transport, token="x")
        self.assertIsNone(err)
        self.assertIsNotNone(ev)
        self.assertEqual(ev.aggregate, "PENDING")
        self.assertFalse(ev.verified())

    def test_failed_check_not_pass(self):
        pr = {"head": {"sha": "b" * 40}}
        runs = {"check_runs": [
            {"name": "CI", "status": "completed", "conclusion": "failure"},
            {"name": "Gitleaks", "status": "completed", "conclusion": "success"},
        ]}

        def transport(method, url, token):
            return pr if "/pulls/" in url else runs

        ev, _ = exact_head_ci_from_check_runs(2, transport=transport, token="x")
        assert ev is not None
        self.assertEqual(ev.aggregate, "FAILURE")
        self.assertFalse(ev.verified())

    def test_success_requires_security_check(self):
        pr = {"head": {"sha": "c" * 40}}
        runs = {"check_runs": [{"name": "CI", "status": "completed", "conclusion": "success"}]}

        def transport(method, url, token):
            return pr if "/pulls/" in url else runs

        ev, _ = exact_head_ci_from_check_runs(3, transport=transport, token="x")
        assert ev is not None
        self.assertEqual(ev.security, "PENDING")
        self.assertFalse(ev.verified())

    def test_failure_is_not_hidden_behind_a_pending_check(self):
        pr = {"head": {"sha": "d" * 40}}
        base = [{"name": "CI", "status": "in_progress", "conclusion": None},
                {"name": "Lint", "status": "completed", "conclusion": "failure"},
                {"name": "Gitleaks", "status": "completed", "conclusion": "success"}]
        for runs in (base, base[::-1]):
            def transport(method, url, token, runs=runs):
                return pr if "/pulls/" in url else {"check_runs": runs}

            ev, err = exact_head_ci_from_check_runs(4, transport=transport, token="x")
            self.assertIsNone(err)
            self.assertEqual(ev.aggregate, "FAILURE")
            self.assertFalse(ev.verified())

    def test_check_runs_are_paginated(self):
        pr = {"head": {"sha": "e" * 40}}
        page1 = [{"name": f"job-{i}", "status": "completed", "conclusion": "success"} for i in range(100)]
        page2 = [{"name": "Gitleaks", "status": "completed", "conclusion": "failure"}]

        def transport(method, url, token):
            if "/pulls/" in url:
                return pr
            return {"check_runs": page1 if url.endswith("&page=1") else page2}

        ev, err = exact_head_ci_from_check_runs(5, transport=transport, token="x")
        self.assertIsNone(err)
        self.assertEqual(ev.aggregate, "FAILURE")  # the failing check sits on page 2
        self.assertEqual(ev.security, "FAILURE")

    def test_endless_full_pages_stop_instead_of_guessing(self):
        pr = {"head": {"sha": "f" * 40}}
        full = [{"name": f"job-{i}", "status": "completed", "conclusion": "success"} for i in range(100)]

        def transport(method, url, token):
            return pr if "/pulls/" in url else {"check_runs": full}

        ev, err = exact_head_ci_from_check_runs(6, transport=transport, token="x")
        self.assertIsNone(ev)
        self.assertEqual(err["reason"], "check_run_inventory_incomplete")

    def test_verified_only_when_aggregate_and_security_success(self):
        self.assertTrue(CiEvidence("SUCCESS", "SUCCESS").verified())
        self.assertFalse(CiEvidence("SUCCESS", "PENDING").verified())
        self.assertFalse(CiEvidence("PENDING", "SUCCESS").verified())


if __name__ == "__main__":
    unittest.main()