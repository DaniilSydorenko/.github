"""Offline adversarial tests for two separate personal-repo lease rulesets."""
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError

import lease_ruleset_candidate as probe

APP_ID = 4242
BRANCH = {"name": probe.REF, "protected": True, "commit": {"sha": "a" * 40}}
BASE = {
    "target": "branch", "source_type": "Repository", "source": probe.REPO,
    "enforcement": "active",
    "conditions": {"ref_name": {"include": [probe.EXPECTED_REF], "exclude": []}},
}
UPDATE = {**BASE, "id": 1, "rules": [{"type": "update"}],
          "bypass_actors": [{"actor_type": "Integration", "actor_id": APP_ID,
                             "bypass_mode": "always"}]}
GUARD = {**BASE, "id": 2, "rules": [{"type": "deletion"},
                                   {"type": "non_fast_forward"}],
         "bypass_actors": []}


class CandidateTests(unittest.TestCase):
    def verify(self, branch=BRANCH, policies=None, app=APP_ID):
        value = probe.audit(branch, [UPDATE, GUARD] if policies is None else policies,
                            approved_app_id=app)
        self.assertFalse(value["cursor_launch_authorized"])
        self.assertFalse(value["github_mutated"])
        self.assertEqual(value["model_runs_started"], 0)
        return value

    def test_two_independent_rules_are_candidate_only(self):
        self.assertEqual(self.verify()["status"], "CANDIDATE")

    def test_unprotected_lease_stops(self):
        self.assertEqual(self.verify(branch={**BRANCH, "protected": False})["status"], "STOP")

    def test_invalid_sha_stops(self):
        self.assertEqual(self.verify(branch={**BRANCH, "commit": {"sha": "short"}})["status"], "STOP")

    def test_unattested_app_id_stops(self):
        for app in (None, True, 0, "4242"):
            with self.subTest(app=app):
                self.assertEqual(self.verify(app=app)["status"], "STOP")

    def test_ruleset_only_update_missing_guard_stops(self):
        self.assertEqual(self.verify(policies=[UPDATE])["status"], "STOP")

    def test_ruleset_only_guard_missing_update_stops(self):
        self.assertEqual(self.verify(policies=[GUARD])["status"], "STOP")

    def test_same_ruleset_id_stops(self):
        self.assertEqual(self.verify(policies=[UPDATE, {**GUARD, "id": 1}])["status"], "STOP")

    def test_combined_update_and_guard_with_app_bypass_stops(self):
        combined = {**UPDATE, "rules": [{"type": "update"},
                                        {"type": "non_fast_forward"},
                                        {"type": "deletion"}]}
        self.assertEqual(self.verify(policies=[combined, GUARD])["status"], "STOP")

    def test_guard_app_bypass_stops_even_for_approved_app(self):
        self.assertEqual(self.verify(policies=[
            UPDATE, {**GUARD, "bypass_actors": UPDATE["bypass_actors"]}])["status"], "STOP")

    def test_human_or_extra_app_writer_stops(self):
        for actors in (
            [{"actor_type": "User", "actor_id": APP_ID, "bypass_mode": "always"}],
            UPDATE["bypass_actors"] + [{"actor_type": "Integration", "actor_id": 32,
                                        "bypass_mode": "always"}],
            [{"actor_type": "RepositoryRole", "actor_id": 5,
              "bypass_mode": "always"}],
        ):
            with self.subTest(actors=actors):
                self.assertEqual(self.verify(policies=[
                    {**UPDATE, "bypass_actors": actors}, GUARD])["status"], "STOP")

    def test_app_bypass_pull_request_only_stops(self):
        actor = {**UPDATE["bypass_actors"][0], "bypass_mode": "pull_request"}
        self.assertEqual(self.verify(policies=[
            {**UPDATE, "bypass_actors": [actor]}, GUARD])["status"], "STOP")

    def test_wrong_target_or_ref_stops(self):
        for change in (
            {"target": "tag"},
            {"enforcement": "evaluate"},
            {"conditions": {"ref_name": {"include": ["~ALL"], "exclude": []}}},
            {"conditions": {"ref_name": {"include": [probe.EXPECTED_REF],
                                          "exclude": [probe.EXPECTED_REF]}}},
            {"source_type": "Organization"},
        ):
            with self.subTest(change=change):
                self.assertEqual(self.verify(policies=[{**UPDATE, **change}, GUARD])["status"], "STOP")

    def test_incomplete_bypass_visibility_stops(self):
        item = {k: v for k, v in UPDATE.items() if k != "bypass_actors"}
        self.assertEqual(self.verify(policies=[item, GUARD])["status"], "STOP")

    def test_non_fast_forward_required(self):
        for t in ("deletion", "non_fast_forward"):
            with self.subTest(t=t):
                self.assertEqual(self.verify(policies=[
                    UPDATE, {**GUARD, "rules": [{"type": t}]}])["status"], "STOP")

    def test_unknown_extra_rule_stops(self):
        self.assertEqual(self.verify(policies=[
            UPDATE, {**GUARD, "rules": GUARD["rules"] + [{"type": "mystery"}]}])["status"], "STOP")

    def test_inventory_cannot_silently_truncate(self):
        policies = [UPDATE, GUARD] + [{**BASE, "id": i, "rules": []}
                                       for i in range(3, 101)]
        self.assertEqual(self.verify(policies=policies)["status"], "STOP")

    def test_no_implicit_public_actor_proof(self):
        self.assertEqual(self.verify(policies=[
            UPDATE, {**GUARD, "bypass_actors": None}])["status"], "STOP")

    def test_restricted_transport_blocks_other_endpoints(self):
        api = probe.ReadOnly("token")
        with patch("lease_ruleset_candidate.urlopen") as transport:
            with self.assertRaises(ValueError):
                api.get("/issues/120")
            transport.assert_not_called()

    def test_restricted_transport_is_get_only(self):
        api = probe.ReadOnly("token")
        with patch("lease_ruleset_candidate.urlopen") as transport, \\
             patch("lease_ruleset_candidate.json.load", return_value=BRANCH):
            self.assertEqual(api.get(f"/branches/{probe.REF}"), BRANCH)
            self.assertEqual(transport.call_args.args[0].get_method(), "GET")

    def test_live_probe_permission_unknown_is_stop(self):
        class Failing:
            def get(self, path):
                raise HTTPError("https://api.github.com", 403, "private", {}, None)
        value = probe.public_readonly_probe(Failing(), APP_ID)
        self.assertEqual(value["status"], "STOP")
        self.assertNotIn("private", json.dumps(value))

    def test_live_probe_uses_details_not_list_summary(self):
        class Reader:
            def __init__(self):
                self.paths = []
            def get(self, path):
                self.paths.append(path)
                return {
                    f"/branches/{probe.REF}": BRANCH,
                    "/rulesets?includes_parents=false&per_page=100":
                        [{"id": 1}, {"id": 2}],
                    "/rulesets/1": UPDATE,
                    "/rulesets/2": GUARD,
                }[path]
        reader = Reader()
        value = probe.public_readonly_probe(reader, APP_ID)
        self.assertEqual(value["status"], "CANDIDATE")
        self.assertEqual(reader.paths[-2:], ["/rulesets/1", "/rulesets/2"])

    def test_cli_missing_token_never_approves(self):
        with patch.dict("os.environ", {}, clear=True), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(probe.main(), 2)
            self.assertFalse(json.loads(output.getvalue())["cursor_launch_authorized"])


if __name__ == "__main__":
    unittest.main()
