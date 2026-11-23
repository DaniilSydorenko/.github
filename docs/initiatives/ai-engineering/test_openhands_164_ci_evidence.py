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

    def test_verified_only_when_aggregate_and_security_success(self):
        self.assertTrue(CiEvidence("SUCCESS", "SUCCESS").verified())
        self.assertFalse(CiEvidence("SUCCESS", "PENDING").verified())
        self.assertFalse(CiEvidence("PENDING", "SUCCESS").verified())


if __name__ == "__main__":
    unittest.main()