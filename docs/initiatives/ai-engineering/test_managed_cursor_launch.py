"""No network or Cursor models: managed transaction / transport negative tests."""
from copy import deepcopy
from io import BytesIO
from unittest import TestCase, main
from unittest.mock import patch
from urllib.error import HTTPError

from github_ref_lease import Controller, agent_id_for
from managed_cursor_launch import (
    CursorCreateHTTP, LaunchUncertain, launch_single_approved_pr,
)
from test_github_ref_lease import MemoryGitRef
from test_preview_one import fixture

REQ = "pilot-issue42-pr212"
RUN = "run-00000000-0000-0000-0000-000000000001"


def permit(**overrides):
    p = {
        "verified_owner_approval": True, "verified_exact_scope": True,
        "verified_cursor_billing": True, "verified_external_billing_excluded": True,
        "verified_account_scope": True, "verified_launch_route_exclusivity": True,
        "verified_model_allowlist": True, "verified_subagents_disabled": True,
        "verified_owner_security_gates": True,
        "request_id": REQ, "repository": "example/test",
        "pr_number": 212, "head_sha": "b" * 40, "issue_number": 42,
        "model_id": "composer-2", "model_allowlist": frozenset({"composer-2"}),
    }
    p.update(overrides)
    return p


class CursorStub:
    def __init__(self):
        self.created = []
        self.fail = False

    def create(self, payload):
        self.created.append(payload)
        if self.fail:
            raise LaunchUncertain("lost response")
        return {"agent_id": payload["agentId"], "run_id": RUN}


class ReaderStub:
    def __init__(self):
        self.calls = 0
        self.responses = [{"items": []}]

    def get_json(self, path, params=None):
        self.calls += 1
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]


class ManagedLaunchTests(TestCase):
    def setUp(self):
        self.store = MemoryGitRef()
        self.controller = Controller(self.store)
        self.reader = ReaderStub()
        self.create = CursorStub()
        # Synthetic test only: accepted ref protections are mocked. Production
        # _trusted_lease_ref_audit rejects a MemoryGitRef and must fetch live GH.
        self.ref_audit = patch("managed_cursor_launch._trusted_lease_ref_audit",
                               return_value=True)
        self.protection = self.ref_audit.start()
        self.addCleanup(self.ref_audit.stop)

    def dispatch(self, **kwargs):
        values = dict(request_id=REQ, bundle=fixture(), permit=permit(),
                      controller=self.controller, cursor_reader=self.reader,
                      cursor_create=self.create)
        values.update(kwargs)
        return launch_single_approved_pr(**values)

    def test_default_code_level_kill_switch_zero_network_zero_lease(self):
        result = self.dispatch()
        self.assertEqual(result["state"], "DISABLED")
        self.assertFalse(result["launched"])
        self.assertEqual(self.reader.calls, 0)
        self.assertEqual(self.create.created, [])
        self.assertEqual(self.store.state["phase"], "IDLE")

    def test_missing_real_ref_protection_stops_even_if_activation_true(self):
        self.protection.return_value = False
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            result = self.dispatch()
        self.assertEqual(result["state"], "STOP")
        self.assertEqual(result["reason"], "lease_ref_exclusive_protection_unverified")
        self.assertEqual(self.reader.calls, 0)
        self.assertEqual(self.create.created, [])
        self.assertEqual(self.store.state["phase"], "IDLE")

    def test_real_ref_guard_rejects_synthetic_untrusted_store(self):
        # Temporarily remove setUp's positive test-double to inspect the
        # actual production function, then restore the mocked environment.
        self.ref_audit.stop()
        try:
            from managed_cursor_launch import _trusted_lease_ref_audit
            self.assertFalse(_trusted_lease_ref_audit(self.controller))
        finally:
            self.protection = self.ref_audit.start()

    def test_protection_removed_after_acquisition_prevents_post(self):
        # The gate is checked before inventory AND again while lease is held.
        self.protection.side_effect = [True, False]
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            result = self.dispatch()
        self.assertEqual(result["state"], "STOP")
        self.assertEqual(self.store.state["phase"], "IDLE")
        self.assertEqual(len(self.create.created), 0)

    def test_one_approved_pr_acquires_lock_before_one_post(self):
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            result = self.dispatch()
        self.assertEqual(result["state"], "STARTED")
        self.assertTrue(result["launched"])
        self.assertEqual(result["pr_url"], "https://github.com/example/test/pull/212")
        self.assertFalse(result["automatic_merge"])
        self.assertEqual(self.store.state["phase"], "RUNNING")
        self.assertEqual(self.store.state["run_id"], RUN)
        self.assertEqual(len(self.create.created), 1)
        self.assertEqual(self.reader.calls, 2)
        self.assertEqual(self.create.created[0]["agentId"], agent_id_for(REQ))
        self.assertFalse(self.create.created[0]["autoCreatePR"])

    def test_duplicate_request_no_second_post(self):
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            self.dispatch()
            duplicate = self.dispatch()
        self.assertEqual(duplicate["state"], "BUSY")
        self.assertEqual(len(self.create.created), 1)

    def test_other_worker_cannot_start(self):
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            self.dispatch()
            other = self.dispatch(request_id="pilot-issue42-pr213",
                                  permit=permit(request_id="pilot-issue42-pr213"))
        self.assertEqual(other["state"], "BUSY")
        self.assertEqual(len(self.create.created), 1)

    def test_lost_create_response_keeps_lock(self):
        self.create.fail = True
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            result = self.dispatch()
        self.assertEqual(result["state"], "STOP_LOCK_HELD")
        self.assertEqual(self.store.state["phase"], "DISPATCHING")
        self.assertEqual(len(self.create.created), 1)

    def test_provider_bad_agent_identity_keeps_lock(self):
        self.create.create = lambda p: {"agent_id": "bc-other", "run_id": RUN}
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            result = self.dispatch()
        self.assertEqual(result["state"], "STOP_LOCK_HELD")
        self.assertEqual(self.store.state["phase"], "DISPATCHING")

    def test_provider_inventory_busy_before_lease(self):
        self.reader.responses = [{"items": [{"id": agent_id_for("other-agent"),
                                             "status": "ACTIVE", "latestRunId": RUN}]}]
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            result = self.dispatch()
        self.assertEqual(result["state"], "BUSY")
        self.assertEqual(self.store.state["phase"], "IDLE")
        self.assertFalse(self.create.created)

    def test_provider_changed_after_lease_releases_reserved_without_post(self):
        self.reader.responses = [
            {"items": []},
            {"items": [{"id": agent_id_for("other-agent"),
                        "status": "ACTIVE", "latestRunId": RUN}]},
        ]
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            result = self.dispatch()
        self.assertEqual(result["state"], "STOP")
        self.assertEqual(self.store.state["phase"], "IDLE")
        self.assertEqual(self.create.created, [])

    def test_unknown_provider_inventory_no_post(self):
        self.reader.responses = [{"items": [{"id": "unrecognized", "status": "ACTIVE"}]}]
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            result = self.dispatch()
        self.assertEqual(result["state"], "STOP")
        self.assertFalse(self.create.created)

    def test_missing_every_finance_and_owner_proof_stops(self):
        keys = ("verified_owner_approval", "verified_exact_scope",
                "verified_cursor_billing", "verified_external_billing_excluded",
                "verified_account_scope", "verified_launch_route_exclusivity",
                "verified_model_allowlist", "verified_subagents_disabled",
                "verified_owner_security_gates")
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            for key in keys:
                with self.subTest(key=key):
                    p = permit()
                    p[key] = False
                    result = self.dispatch(permit=p)
                    self.assertEqual(result["state"], "STOP")
        self.assertEqual(self.reader.calls, 0)
        self.assertFalse(self.create.created)

    def test_account_without_full_scope_stops(self):
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            result = self.dispatch(permit=permit(verified_account_scope=None))
        self.assertEqual(result["state"], "STOP")

    def test_stale_granted_pr_head_stops(self):
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            result = self.dispatch(permit=permit(head_sha="a" * 40))
        self.assertEqual(result["state"], "STOP")
        self.assertFalse(self.create.created)

    def test_wrong_repo_or_issue_does_not_start(self):
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            for value in (permit(repository="other/repo"), permit(issue_number=73),
                          permit(pr_number=999)):
                with self.subTest(value=value):
                    self.assertEqual(self.dispatch(permit=value)["state"], "STOP")
        self.assertFalse(self.create.created)

    def test_missing_model_or_nonallowlisted_model(self):
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            for value in (permit(model_id="unknown"), permit(model_allowlist=frozenset())):
                self.assertEqual(self.dispatch(permit=value)["state"], "STOP")

    def test_empty_pr_inventory_prevents_new_code_from_one_pr_pilot(self):
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            result = self.dispatch(bundle=fixture(include_pr=False))
        self.assertEqual(result["state"], "STOP")
        self.assertEqual(self.reader.calls, 0)

    def test_owner_gate_prevents_provider_request(self):
        f = fixture()
        f["semantic"]["owner_gate"] = True
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            result = self.dispatch(bundle=f)
        self.assertEqual(result["state"], "STOP")
        self.assertEqual(self.reader.calls, 0)

    def test_missing_approval_not_turn_into_default_true(self):
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            self.assertEqual(self.dispatch(permit={})["state"], "STOP")

    def test_cursor_transport_rejects_expanded_payload(self):
        t = CursorCreateHTTP("dummy-test-key")
        invalid = {"agentId": agent_id_for(REQ), "prompt": {"text": "ok"},
                   "model": {"id": "composer-2"}, "repos": [
                       {"url": "https://github.com/example/test",
                        "prUrl": "https://github.com/example/test/pull/212"}],
                   "workOnCurrentBranch": True, "autoCreatePR": False,
                   "mode": "agent", "envVars": {"TOKEN": "unsafe"}}
        with self.assertRaises(LaunchUncertain), patch("managed_cursor_launch.urlopen") as call:
            t.create(invalid)
        call.assert_not_called()

    def test_cursor_create_http_409_unknown_no_retry(self):
        from cursor_pr_payload import existing_pr_payload
        payload = existing_pr_payload(
            request_id=REQ, repository="example/test", pr_number=212,
            exact_pr_head="b" * 40, issue_number=42,
            model_id="composer-2", model_allowlist=frozenset({"composer-2"}),
        )["payload"]
        err = HTTPError("https://api.cursor.com/v1/agents", 409, "duplicate", {}, None)
        t = CursorCreateHTTP("dummy-test-key")
        with patch("managed_cursor_launch.urlopen", side_effect=err) as call:
            with self.assertRaises(LaunchUncertain):
                t.create(payload)
        self.assertEqual(call.call_count, 1)


if __name__ == "__main__":
    main()
