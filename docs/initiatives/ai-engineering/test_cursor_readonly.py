"""No network, no model inference: Cursor inventory safety tests."""
import io
import unittest
from unittest.mock import MagicMock, patch

from cursor_readonly import (CursorReadError, LiveCursorReadOnly, api_key_info_ok,
                             global_run_preflight, model_ids, token_usage_readonly)

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

    def test_stop_detail_names_cause_without_provider_content(self):
        api = MagicMock()
        api.get_json.return_value = {"items": [{"id": A, "status": "PAUSED"}]}
        d = global_run_preflight(api, global_account_scope_verified=True)
        self.assertEqual((d["status"], d["detail"], d["agents_checked"]),
                         ("STOP", "unknown agent status PAUSED", 1))
        api.get_json.return_value = {"items": [{"id": A, "status": "secret body <x>"}]}
        d = global_run_preflight(api, global_account_scope_verified=True)
        self.assertEqual(d["detail"], "unknown agent status <non-enum>")
        api.get_json.return_value = {"items": [{"id": "agent-1", "status": "ACTIVE"}]}
        d = global_run_preflight(api, global_account_scope_verified=True)
        self.assertEqual((d["detail"], d["agents_checked"]),
                         ("unknown or duplicated agent identity", 0))
        api.get_json.side_effect = CursorReadError("Cursor HTTP 403 (body withheld)", status=403)
        d = global_run_preflight(api, global_account_scope_verified=True)
        self.assertEqual(d["detail"], "Cursor HTTP 403 (body withheld)")
        self.assertFalse(d["can_launch"])

    @patch("cursor_readonly.time.sleep", lambda _s: None)
    def test_get_retries_once_on_transport_error_never_on_http_error(self):
        from urllib.error import HTTPError, URLError
        reader = LiveCursorReadOnly("k")
        ok = MagicMock()
        ok.__enter__.return_value = io.BytesIO(b'{"items": []}')
        with patch("cursor_readonly.urlopen", side_effect=[TimeoutError(), ok]) as u:
            self.assertEqual(reader.get_json("/v1/agents"), {"items": []})
            self.assertEqual(u.call_count, 2)
        with patch("cursor_readonly.urlopen", side_effect=[URLError("x"), TimeoutError()]) as u:
            with self.assertRaisesRegex(CursorReadError, r"\(TimeoutError\)"):
                reader.get_json("/v1/agents")
            self.assertEqual(u.call_count, 2)
        with patch("cursor_readonly.urlopen",
                   side_effect=HTTPError("u", 429, "m", {}, None)) as u:
            with self.assertRaises(CursorReadError) as ctx:
                reader.get_json("/v1/agents")
            self.assertEqual((ctx.exception.status, u.call_count), (429, 1))

    def test_stop_detail_reports_failing_phase(self):
        api = MagicMock()
        api.get_json.side_effect = [idle(), CursorReadError("Cursor transport/response unknown")]
        d = global_run_preflight(api, global_account_scope_verified=True)
        self.assertEqual((d["status"], d["phase"], d["agents_checked"]), ("STOP", "run", 1))

    def _slow_api(self, statuses, delay=0.05):
        import threading, time
        agents = [{"id": f"bc-00000000-0000-0000-0000-{i:012d}", "status": "IDLE",
                   "latestRunId": f"run-00000000-0000-0000-0000-{i:012d}"} for i in range(len(statuses))]
        lock, calls = threading.Lock(), []

        class Api:
            def get_json(_self, path, params=None):
                with lock:
                    calls.append(path)
                if path == "/v1/agents":
                    return {"items": agents}
                time.sleep(delay)
                i = int(path.rsplit("-", 1)[1])
                if statuses[i] == "ERR":
                    raise CursorReadError("Cursor HTTP 500 (body withheld)", status=500)
                return {"id": agents[i]["latestRunId"], "agentId": agents[i]["id"],
                        "status": statuses[i]}
        return Api(), calls

    def test_concurrent_scan_equals_sequential_and_is_faster(self):
        import time
        api, calls = self._slow_api(["FINISHED"] * 12)
        t0 = time.monotonic()
        seq = global_run_preflight(api, global_account_scope_verified=True, concurrency=1)
        t_seq = time.monotonic() - t0
        t0 = time.monotonic()
        par = global_run_preflight(api, global_account_scope_verified=True, concurrency=6)
        t_par = time.monotonic() - t0
        self.assertEqual(seq, par)
        self.assertEqual(par["status"], "CLEAR")
        self.assertEqual(len([c for c in calls if "/runs/" in c]), 24)  # nobody skipped
        self.assertLess(t_par, t_seq / 2)

    def test_concurrent_scan_reports_first_busy_in_list_order_and_fails_closed(self):
        api, _ = self._slow_api(["FINISHED", "RUNNING", "FINISHED", "CREATING"], delay=0)
        out = global_run_preflight(api, global_account_scope_verified=True, concurrency=4)
        self.assertEqual((out["status"], out["active_agent"][-1]), ("BUSY", "1"))
        api, _ = self._slow_api(["FINISHED", "FINISHED", "ERR", "FINISHED"], delay=0)
        out = global_run_preflight(api, global_account_scope_verified=True, concurrency=4)
        self.assertEqual((out["status"], out["phase"]), ("STOP", "run"))
        self.assertIn("500", out["detail"])
        for bad in (0, 17, "4"):
            self.assertEqual(global_run_preflight(api, global_account_scope_verified=True,
                                                  concurrency=bad)["reason"], "invalid_concurrency")

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
                     "/v1/agents?limit=100", "/v1/models/../me", "/v1/models?x=1",
                     "/v1/meta", "/v1/modelsX"):
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


    def test_reader_allows_only_exact_models_and_me_paths(self):
        reader = LiveCursorReadOnly("test-key")
        with patch("cursor_readonly.urlopen") as urlopen, \
                patch("cursor_readonly.json.load", return_value={}):
            response = MagicMock()
            response.__enter__.return_value = response
            urlopen.return_value = response
            for path in ("/v1/models", "/v1/me"):
                self.assertEqual(reader.get_json(path), {})
                self.assertEqual(urlopen.call_args.args[0].get_method(), "GET")

    def test_model_ids_are_exact_ids_not_aliases(self):
        api = MagicMock()
        api.get_json.return_value = {"items": [
            {"id": "composer-2", "aliases": ["composer-latest", "composer"]}]}
        self.assertEqual(model_ids(api), frozenset({"composer-2"}))

    def test_model_ids_fail_closed(self):
        for body in ({}, {"items": []}, {"items": [{"id": ""}]}, {"items": ["x"]},
                     {"items": [{"displayName": "no id"}]}):
            api = MagicMock()
            api.get_json.return_value = body
            self.assertEqual(model_ids(api), frozenset(), body)
        api = MagicMock()
        api.get_json.side_effect = CursorReadError("down")
        self.assertEqual(model_ids(api), frozenset())

    def test_api_key_info(self):
        api = MagicMock()
        api.get_json.return_value = {"apiKeyName": "ci", "createdAt": "2026-04-13T18:30:00.000Z"}
        self.assertTrue(api_key_info_ok(api))
        api.get_json.return_value = {"error": "unauthorized"}
        self.assertFalse(api_key_info_ok(api))
        api.get_json.side_effect = CursorReadError("HTTP 401")
        self.assertFalse(api_key_info_ok(api))


if __name__ == "__main__":
    unittest.main()
