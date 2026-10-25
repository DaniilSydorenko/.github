"""No network, no model inference: Cursor inventory safety tests."""
import unittest
from unittest.mock import MagicMock, patch

from cursor_readonly import (CursorReadError, LiveCursorReadOnly,
                             global_run_preflight, token_usage_readonly)

A = "bc-00000000-0000-0000-0000-000000000001"
B = "bc-00000000-0000-0000-0000-000000000002"
R = "run-00000000-0000-0000-0000-000000000001"


def active():
    return {"items": [{"id": A, "status": "ACTIVE", "latestRunId": R}]}


def idle():
    return {"items": [{"id": A, "status": "IDLE", "latestRunId": R}]}


def finished():
    return {"id": R, "agentId": A, "status": "FINISHED"}


class CursorInventoryTests(unittest.TestCase):
    def test_missing_global_scope_stops_without_api(self):
        api = MagicMock()
        d = global_run_preflight(api, global_account_scope_verified=False)
        self.assertEqual(d["status"], "STOP")
        api.get_json.assert_not_called()

    def test_active_agent_blocks(self):
        api = MagicMock()
        api.get_json.return_value = active()
        self.assertEqual(global_run_preflight(api, global_account_scope_verified=True)["status"], "BUSY")
        self.assertEqual(api.get_json.call_count, 1)

    def test_idle_terminal_run_clear_but_never_dispatch_authorized(self):
        api = MagicMock()
        api.get_json.side_effect = [idle(), finished()]
        result = global_run_preflight(api, global_account_scope_verified=True)
        self.assertEqual(result["status"], "CLEAR")
        self.assertIs(result["can_launch"], False)

    def test_idle_nonterminal_busy(self):
        for status in ("CREATING", "RUNNING", "WAITING_FOR_BACKGROUND_WORK"):
            with self.subTest(status=status):
                api = MagicMock()
                api.get_json.side_effect = [idle(), {**finished(), "status": status}]
                self.assertEqual(global_run_preflight(api, global_account_scope_verified=True)["status"], "BUSY")

    def test_idle_unknown_run_state_stops(self):
        api = MagicMock()
        api.get_json.side_effect = [idle(), {**finished(), "status": "FUTURE"}]
        self.assertEqual(global_run_preflight(api, global_account_scope_verified=True)["status"], "STOP")

    def test_wrong_run_identity_stops(self):
        api = MagicMock()
        api.get_json.side_effect = [idle(), {**finished(), "agentId": B}]
        self.assertEqual(global_run_preflight(api, global_account_scope_verified=True)["status"], "STOP")

    def test_archived_agent_does_not_require_run(self):
        api = MagicMock()
        api.get_json.return_value = {"items": [{"id": A, "status": "ARCHIVED"}]}
        d = global_run_preflight(api, global_account_scope_verified=True)
        self.assertEqual(d["status"], "CLEAR")
        self.assertEqual(api.get_json.call_count, 1)

    def test_empty_inventory_clear_but_not_authorized(self):
        api = MagicMock()
        api.get_json.return_value = {"items": []}
        d = global_run_preflight(api, global_account_scope_verified=True)
        self.assertEqual(d["status"], "CLEAR")
        self.assertFalse(d["can_launch"])

    def test_pagination_complete(self):
        api = MagicMock()
        api.get_json.side_effect = [
            {"items": [{"id": A, "status": "ARCHIVED"}], "nextCursor": "next"},
            {"items": [{"id": B, "status": "ARCHIVED"}]},
        ]
        d = global_run_preflight(api, global_account_scope_verified=True)
        self.assertEqual(d["observed_agents"], 2)

    def test_pagination_truncated_stops(self):
        api = MagicMock()
        api.get_json.return_value = {"items": [], "nextCursor": "more"}
        d = global_run_preflight(api, global_account_scope_verified=True, max_pages=2)
        self.assertEqual(d["status"], "STOP")

    def test_cyclic_cursor_stops(self):
        api = MagicMock()
        api.get_json.return_value = {"items": [], "nextCursor": "repeat"}
        self.assertEqual(global_run_preflight(api, global_account_scope_verified=True)["status"], "STOP")

    def test_duplicate_agent_identity_stops(self):
        api = MagicMock()
        api.get_json.return_value = {"items": [{"id": A, "status": "ARCHIVED"},
                                               {"id": A, "status": "ARCHIVED"}]}
        self.assertEqual(global_run_preflight(api, global_account_scope_verified=True)["status"], "STOP")

    def test_unknown_agent_status_stops(self):
        api = MagicMock()
        api.get_json.return_value = {"items": [{"id": A, "status": "UNKNOWN"}]}
        self.assertEqual(global_run_preflight(api, global_account_scope_verified=True)["status"], "STOP")

    def test_transport_error_stops(self):
        api = MagicMock()
        api.get_json.side_effect = CursorReadError("API inaccessible")
        self.assertEqual(global_run_preflight(api, global_account_scope_verified=True)["status"], "STOP")

    def test_zero_pages_stops_without_request(self):
        api = MagicMock()
        self.assertEqual(global_run_preflight(api, global_account_scope_verified=True,
                                             max_pages=0)["status"], "STOP")
        api.get_json.assert_not_called()

    def test_token_usage_observed_cost_unknown(self):
        api = MagicMock()
        api.get_json.return_value = {"runs": [{"id": R, "usage": {
            "inputTokens": 1, "outputTokens": 2, "cacheWriteTokens": 3,
            "cacheReadTokens": 4, "totalTokens": 10}}]}
        d = token_usage_readonly(api, A, R)
        self.assertEqual(d["tokens"]["totalTokens"], 10)
        self.assertEqual(d["charged_cost"], "UNKNOWN")

    def test_token_negative_or_sum_mismatch_stops(self):
        for n in (-1, 8, True):
            with self.subTest(n=n):
                api = MagicMock()
                api.get_json.return_value = {"runs": [{"id": R, "usage": {
                    "inputTokens": n, "outputTokens": 2, "cacheWriteTokens": 3,
                    "cacheReadTokens": 4, "totalTokens": 10}}]}
                with self.assertRaises(CursorReadError):
                    token_usage_readonly(api, A, R)

    def test_usage_wrong_run_stops(self):
        api = MagicMock()
        api.get_json.return_value = {"runs": [{"id": "run-00000000-0000-0000-0000-000000000099",
                                                "usage": {}}]}
        with self.assertRaises(CursorReadError):
            token_usage_readonly(api, A, R)

    def test_reader_rejects_write_paths(self):
        reader = LiveCursorReadOnly("test-key")
        for path in ("/v1/admin/billing", "/v1/agents/../secrets",
                     "/v1/agents?limit=100"):
            with self.subTest(path=path), self.assertRaises(CursorReadError):
                reader.get_json(path)

    def test_reader_is_get_only(self):
        reader = LiveCursorReadOnly("test-key")
        with patch("cursor_readonly.urlopen") as urlopen:
            response = MagicMock()
            response.__enter__.return_value = response
            with patch("cursor_readonly.json.load", return_value={"items": []}):
                urlopen.return_value = response
                self.assertEqual(reader.get_json("/v1/agents"), {"items": []})
                self.assertEqual(urlopen.call_args.args[0].get_method(), "GET")


if __name__ == "__main__":
    unittest.main()
