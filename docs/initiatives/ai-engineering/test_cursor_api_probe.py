"""Synthetic/no-network tests. Cursor and GitHub credentials never used."""
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from cursor_api_probe import main, observe
from cursor_readonly import CursorReadError

A = "bc-00000000-0000-0000-0000-000000000001"
B = "bc-00000000-0000-0000-0000-000000000002"


class FakeAPI:
    def __init__(self, *pages):
        self.pages = list(pages)
        self.calls = []

    def get_json(self, path, params=None):
        self.calls.append((path, params))
        if not self.pages:
            raise CursorReadError("exhausted")
        result = self.pages.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


class CursorProbeTests(unittest.TestCase):
    def test_empty_inventory_is_observed_but_not_authorized(self):
        api = FakeAPI({"items": []})
        d = observe(api)
        self.assertEqual(d["status"], "OBSERVED")
        self.assertFalse(d["account_scope_verified"])
        self.assertFalse(d["execution_authorized"])
        self.assertFalse(d["billing_verified"])
        self.assertEqual(d["model_runs_started"], 0)
        self.assertEqual(api.calls[0][0], "/v1/agents")

    def test_active_agent_redacted_from_report(self):
        d = observe(FakeAPI({"items": [{"id": A, "status": "ACTIVE"}]}))
        self.assertEqual(d["visible_active_agents"], 1)
        self.assertNotIn(A, json.dumps(d))

    def test_pagination_sanitized(self):
        api = FakeAPI({"items": [{"id": A, "status": "IDLE"}],
                       "nextCursor": "secret-page-token"},
                      {"items": [{"id": B, "status": "ARCHIVED"}]})
        d = observe(api)
        self.assertEqual((d["visible_idle_agents"], d["visible_archived_agents"]), (1, 1))
        self.assertEqual(len(api.calls), 2)
        self.assertNotIn("secret-page-token", json.dumps(d))

    def test_http_error_cannot_expose_raw_provider_message(self):
        d = observe(FakeAPI(CursorReadError("secret provider response")))
        self.assertEqual(d["status"], "STOP")
        self.assertNotIn("secret", json.dumps(d))

    def test_unknown_status_blocks(self):
        self.assertEqual(observe(FakeAPI({"items": [{"id": A, "status": "FUTURE"}]}))["status"], "STOP")

    def test_duplicate_agent_blocks(self):
        self.assertEqual(observe(FakeAPI({"items": [
            {"id": A, "status": "IDLE"}, {"id": A, "status": "IDLE"}]}))["status"], "STOP")

    def test_cyclic_cursor_blocks(self):
        self.assertEqual(observe(FakeAPI({"items": [], "nextCursor": "x"},
                                          {"items": [], "nextCursor": "x"}))["status"], "STOP")

    def test_truncated_inventory_never_green(self):
        self.assertEqual(observe(FakeAPI({"items": [], "nextCursor": "x"}),
                                 max_pages=1)["status"], "STOP")

    def test_malformed_list_blocks(self):
        self.assertEqual(observe(FakeAPI({"items": "bad-list"}))["status"], "STOP")

    def test_invalid_page_bound_blocks_without_network(self):
        api = FakeAPI({"items": []})
        for bound in (0, 11, True, None):
            with self.subTest(bound=bound):
                self.assertEqual(observe(api, max_pages=bound)["status"], "STOP")
        self.assertEqual(api.calls, [])

    def test_null_item_blocks(self):
        self.assertEqual(observe(FakeAPI({"items": [None]}))["status"], "STOP")

    def test_missing_credential_returns_blocked_not_success(self):
        out = io.StringIO()
        with patch.dict("os.environ", {}, clear=True), redirect_stdout(out):
            self.assertEqual(main(), 2)
        d = json.loads(out.getvalue())
        self.assertEqual(d["status"], "BLOCKED")
        self.assertEqual(d["model_runs_started"], 0)

    def test_success_does_not_print_secret(self):
        out = io.StringIO()
        with patch.dict("os.environ", {"CURSOR_API_KEY": "secret-provider-key"}, clear=True), \
             patch("cursor_api_probe.LiveCursorReadOnly", return_value=FakeAPI({"items": []})), \
             redirect_stdout(out):
            self.assertEqual(main(), 0)
        self.assertNotIn("secret-provider-key", out.getvalue())
        self.assertEqual(json.loads(out.getvalue())["status"], "OBSERVED")

    def test_failed_probe_does_not_print_secret(self):
        out = io.StringIO()
        with patch.dict("os.environ", {"CURSOR_API_KEY": "secret-key"}, clear=True), \
             patch("cursor_api_probe.LiveCursorReadOnly",
                   return_value=FakeAPI(CursorReadError("secret-key"))), \
             redirect_stdout(out):
            self.assertEqual(main(), 2)
        self.assertNotIn("secret-key", out.getvalue())


if __name__ == "__main__":
    unittest.main()
