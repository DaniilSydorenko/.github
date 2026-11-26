"""Offline regression for Haversine #220 protected Cursor dispatch gates."""
from __future__ import annotations

from unittest import TestCase, main
from unittest.mock import patch

from cursor_protected_dispatch import (
    APPROVED_OPERATION,
    ISSUE,
    ProtectedCursorContext,
    competing_writer_verdict,
    protected_context_from_env,
    run_gates_only,
)
from github_ref_lease import check_state, fingerprint
from managed_cursor_launch import PILOT_ACTIVATION_ENABLED


class CursorProtectedDispatchTests(TestCase):
    def setUp(self) -> None:
        self.ctx = ProtectedCursorContext(
            repository="DaniilSydorenko/.github",
            actor="DaniilSydorenko",
            ref="refs/heads/main",
            event_name="workflow_dispatch",
            run_attempt="1",
            operation=APPROVED_OPERATION,
            owner_go_issue=ISSUE,
            workflow_run_id="999",
            execute_cursor_requested=False,
        )
        self.idle = {
            "phase": "IDLE",
            "version": 1,
            "revision": 0,
            "request_id": None,
            "consumed_request_hashes": [],
        }
        self.preflight_ok = {
            "decision": "STOP",
            "reason": "scope_preflight_passed_but_live_gates_unverified",
        }
        self.main_sha = "f" * 40

    def test_pilot_activation_stays_off(self) -> None:
        self.assertIs(PILOT_ACTIVATION_ENABLED, False)

    def test_env_context_requires_owner_operation(self) -> None:
        env = {
            "GITHUB_REPOSITORY": "DaniilSydorenko/.github",
            "GITHUB_ACTOR": "DaniilSydorenko",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_RUN_ID": "42",
            "AI_ENG_APPROVED_OPERATION": APPROVED_OPERATION,
            "AI_ENG_OWNER_GO_ISSUE": "220",
        }
        with patch.dict("os.environ", env, clear=True):
            ctx = protected_context_from_env()
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.owner_go_issue, 220)

    def test_gates_only_disabled_launch(self) -> None:
        result = run_gates_only(
            self.ctx,
            issue_preflight=lambda: self.preflight_ok,
            lease_state_reader=lambda: self.idle,
            main_sha_reader=lambda: self.main_sha,
        )
        self.assertEqual(result["decision"], "STOP")
        self.assertEqual(result["reason"], "owner_activation_not_enabled")
        self.assertFalse(result["live_cursor_dispatch_authorized"])
        self.assertNotEqual(result.get("competing_writer"), True)

    def test_competing_writer_blocks(self) -> None:
        rid = "cursor-test-request"
        busy = {
            **self.idle,
            "phase": "VERIFYING",
            "request_id": rid,
            "agent_id": "bc-00000000-0000-0000-0000-000000000000",
            "source_issue_url": (
                "https://github.com/DaniilSydorenko/haversine-geolocation/issues/232"
            ),
            "pr_url": "https://github.com/DaniilSydorenko/haversine-geolocation/pull/233",
            "run_id": "run-00000000-0000-0000-0000-000000000001",
            "revision": 3,
            "consumed_request_hashes": [fingerprint(rid)],
        }
        check_state(busy)
        writer = competing_writer_verdict(busy)
        self.assertTrue(writer["competing_writer"])
        result = run_gates_only(
            self.ctx,
            issue_preflight=lambda: self.preflight_ok,
            lease_state_reader=lambda: busy,
            main_sha_reader=lambda: self.main_sha,
        )
        self.assertEqual(result["reason"], "global_lease_not_idle")
        self.assertTrue(result["competing_writer"])


if __name__ == "__main__":
    main()