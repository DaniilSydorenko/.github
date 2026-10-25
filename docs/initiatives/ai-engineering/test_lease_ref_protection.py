"""Fail-closed lease protection checks; synthetic GitHub only, no network."""
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError

import lease_ref_protection as probe

A = "a" * 40
GOOD_BRANCH = {"name": probe.REF, "protected": True, "commit": {"sha": A}}
GOOD_RULES = {
    "allow_force_pushes": {"enabled": False},
    "allow_deletions": {"enabled": False},
    "enforce_admins": {"enabled": True},
    "restrictions": {"users": [], "teams": [], "apps": [{"slug": "owner-executor"}]},
}


class LeaseSecurityTests(unittest.TestCase):
    def check(self, branch, policy, app="owner-executor"):
        result = probe.audit(branch, policy, approved_writer_app=app)
        self.assertFalse(result["cursor_launch_authorized"])
        self.assertEqual(result["model_runs_started"], 0)
        self.assertFalse(result["git_writes"])
        return result

    def test_unprotected_current_live_shape_stops(self):
        b = {**GOOD_BRANCH, "protected": False}
        self.assertEqual(self.check(b, None)["reason"], "lease_branch_unprotected")

    def test_good_branch_rules_are_observation_not_launch_permission(self):
        r = self.check(GOOD_BRANCH, GOOD_RULES)
        self.assertEqual(r["status"], "VERIFIED")
        self.assertFalse(r["cursor_launch_authorized"])

    def test_wrong_branch_name_stops(self):
        self.assertEqual(self.check({**GOOD_BRANCH, "name": "main"}, GOOD_RULES)["status"], "STOP")

    def test_missing_head_sha_stops(self):
        self.assertEqual(self.check({**GOOD_BRANCH, "commit": {}}, GOOD_RULES)["status"], "STOP")

    def test_protection_endpoint_denied_stops(self):
        self.assertEqual(self.check(GOOD_BRANCH, None)["reason"], "branch_protection_unavailable")

    def test_force_push_allowed_stops(self):
        rules = {**GOOD_RULES, "allow_force_pushes": {"enabled": True}}
        self.assertEqual(self.check(GOOD_BRANCH, rules)["reason"], "force_push_bypass_possible")

    def test_deletion_allowed_stops(self):
        rules = {**GOOD_RULES, "allow_deletions": {"enabled": True}}
        self.assertEqual(self.check(GOOD_BRANCH, rules)["reason"], "branch_deletion_possible")

    def test_admins_can_bypass_stops(self):
        rules = {**GOOD_RULES, "enforce_admins": {"enabled": False}}
        self.assertEqual(self.check(GOOD_BRANCH, rules)["reason"], "admin_bypass_not_disabled")

    def test_missing_protection_control_stops(self):
        for field in ("allow_force_pushes", "allow_deletions", "enforce_admins"):
            rules = {k: v for k, v in GOOD_RULES.items() if k != field}
            with self.subTest(field=field):
                self.assertEqual(self.check(GOOD_BRANCH, rules)["status"], "STOP")

    def test_unknown_effective_restrictions_stops(self):
        rules = {k: v for k, v in GOOD_RULES.items() if k != "restrictions"}
        self.assertEqual(self.check(GOOD_BRANCH, rules)["reason"],
                         "exclusive_writer_not_verified")

    def test_any_human_can_push_stops(self):
        rules = {**GOOD_RULES, "restrictions": {
            "users": [{"login": "someone"}], "teams": [],
            "apps": [{"slug": "owner-executor"}]}}
        self.assertEqual(self.check(GOOD_BRANCH, rules)["reason"], "human_or_team_push_bypass")

    def test_team_can_push_stops(self):
        rules = {**GOOD_RULES, "restrictions": {
            "users": [], "teams": [{"slug": "team"}],
            "apps": [{"slug": "owner-executor"}]}}
        self.assertEqual(self.check(GOOD_BRANCH, rules)["reason"], "human_or_team_push_bypass")

    def test_unapproved_app_stops(self):
        self.assertEqual(self.check(GOOD_BRANCH, GOOD_RULES, app=None)["reason"],
                         "approved_github_app_not_configured")

    def test_other_apps_cannot_write(self):
        rules = {**GOOD_RULES, "restrictions": {
            "users": [], "teams": [],
            "apps": [{"slug": "owner-executor"}, {"slug": "other"}]}}
        self.assertEqual(self.check(GOOD_BRANCH, rules)["reason"],
                         "exclusive_app_identity_not_verified")

    def test_owner_app_mismatch_blocks(self):
        self.assertEqual(self.check(GOOD_BRANCH, GOOD_RULES, app="different")["status"], "STOP")

    def test_unprotected_branch_does_not_call_admin_protection(self):
        calls = []
        def get(path):
            calls.append(path)
            return {**GOOD_BRANCH, "protected": False}
        x = probe.public_readonly_probe(get)
        self.assertEqual(x["status"], "STOP")
        self.assertEqual(calls, [f"/branches/{probe.REF}"])

    def test_protected_branch_calls_both_gets(self):
        calls = []
        def get(path):
            calls.append(path)
            return GOOD_BRANCH if len(calls) == 1 else GOOD_RULES
        result = probe.public_readonly_probe(get, approved_writer_app="owner-executor")
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(calls, [f"/branches/{probe.REF}",
                                 f"/branches/{probe.REF}/protection"])

    def test_permission_error_stops_without_raw_message(self):
        def get(_):
            raise HTTPError("https://api.github.com", 403, "private admin secret", {}, None)
        r = probe.public_readonly_probe(get)
        self.assertEqual(r["status"], "STOP")
        self.assertNotIn("secret", json.dumps(r))

    def test_wrong_http_path_cannot_be_read(self):
        api = probe.ReadOnlyGitHub("test-token")
        with patch("lease_ref_protection.urlopen") as request:
            with self.assertRaises(ValueError):
                api.get("/issues/120")
            request.assert_not_called()

    def test_allowed_request_is_get_only(self):
        api = probe.ReadOnlyGitHub("test-token")
        with patch("lease_ref_protection.urlopen") as urlopen, \
             patch("lease_ref_protection.json.load", return_value=GOOD_BRANCH):
            response = urlopen.return_value.__enter__.return_value
            self.assertEqual(api.get(f"/branches/{probe.REF}"), GOOD_BRANCH)
            self.assertEqual(urlopen.call_args.args[0].get_method(), "GET")

    def test_main_missing_token_still_cannot_launch(self):
        with patch("lease_ref_protection.ReadOnlyGitHub") as factory, \
             patch.dict("os.environ", {}, clear=True), redirect_stdout(io.StringIO()) as out:
            factory.return_value.get.return_value = {**GOOD_BRANCH, "protected": False}
            self.assertEqual(probe.main(), 2)
            self.assertIn("lease_branch_unprotected", out.getvalue())


if __name__ == "__main__":
    unittest.main()
