"""Adversarial OFFLINE App-writer provenance checks; no credentials/network."""
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError

import app_writer_provenance as probe

APP_ID = 4242
SLUG = "daniil-ai-eng-lease"
INSTALL = 5555
APP = {
    "id": APP_ID, "slug": SLUG,
    "owner": {"login": "DaniilSydorenko", "type": "User"},
    "permissions": {"metadata": "read", "contents": "write"},
}
SCOPE = {"total_count": 1, "repositories": [{
    "id": probe.REPO_ID, "full_name": probe.REPO, "private": False,
}]}


class AppWriterTests(unittest.TestCase):
    def check(self, app=APP, scope=SCOPE, **kwargs):
        options = {"expected_app_id": APP_ID, "expected_slug": SLUG,
                   "minted_app_slug": SLUG,
                   "minted_installation_id": INSTALL}
        options.update(kwargs)
        answer = probe.verify(app, scope, **options)
        self.assertFalse(answer["cursor_launch_authorized"])
        self.assertFalse(answer["lease_write_authorized"])
        self.assertEqual(answer["model_runs_started"], 0)
        self.assertFalse(answer["github_mutated"])
        return answer

    def test_minimal_owner_app_scoped_token_only_observes(self):
        result = self.check()
        self.assertEqual(result["status"], "CREDENTIAL_PATH_OBSERVED")
        self.assertTrue(result["owner_review_required"])

    def test_missing_or_incorrect_action_output_stops(self):
        cases = [
            {"minted_app_slug": ""},
            {"minted_app_slug": "cursor"},
            {"minted_installation_id": 0},
            {"minted_installation_id": True},
            {"expected_app_id": None},
            {"expected_app_id": True},
            {"expected_slug": "wrong-app"},
            {"expected_slug": "../injection"},
        ]
        for opts in cases:
            with self.subTest(opts=opts):
                self.assertEqual(self.check(**opts)["status"], "STOP")

    def test_mismatching_app_id_or_slug_stops(self):
        for mutation in ({"id": 999}, {"slug": "cursor"}, {"id": "4242"}):
            with self.subTest(mutation=mutation):
                self.assertEqual(self.check(app={**APP, **mutation})["status"], "STOP")

    def test_non_owner_app_stops(self):
        for own in ({"login": "someone", "type": "User"},
                    {"login": "DaniilSydorenko", "type": "Organization"}):
            self.assertEqual(self.check(app={**APP, "owner": own})["status"], "STOP")

    def test_missing_write_permission_stops(self):
        for content in ("read", None):
            self.assertEqual(self.check(app={
                **APP, "permissions": {"metadata": "read", "contents": content}
            })["status"], "STOP")

    def test_extra_app_permissions_stop(self):
        for name in ("administration", "workflows", "issues", "pull_requests"):
            with self.subTest(permission=name):
                self.assertEqual(self.check(app={
                    **APP, "permissions": {**APP["permissions"], name: "write"},
                })["status"], "STOP")

    def test_multi_repo_token_stops(self):
        scope = {"total_count": 2, "repositories": [
            SCOPE["repositories"][0], {"id": 1, "full_name": "bad/other"},
        ]}
        self.assertEqual(self.check(scope=scope)["status"], "STOP")

    def test_claimed_one_but_two_in_payload_stops(self):
        scope = {"total_count": 1, "repositories": SCOPE["repositories"] * 2}
        self.assertEqual(self.check(scope=scope)["status"], "STOP")

    def test_repo_id_and_path_both_required(self):
        for mutation in ({"id": 0}, {"id": "1406421648"},
                         {"full_name": "DaniilSydorenko/another"},
                         {"private": True}):
            with self.subTest(mutation=mutation):
                self.assertEqual(self.check(scope={
                    "total_count": 1,
                    "repositories": [{**SCOPE["repositories"][0], **mutation}]
                })["status"], "STOP")

    def test_no_private_token_echo_in_report(self):
        value = self.check()
        self.assertNotIn("ghs_", json.dumps(value))
        self.assertNotIn(SLUG, json.dumps(value))

    def test_only_two_get_endpoints_allowed(self):
        reader = probe.AppMetadataReadOnly("dont-echo-test-secret")
        with patch("app_writer_provenance.urlopen") as network:
            for path in ("/repos/DaniilSydorenko/.github", "/installation/token",
                         "/apps/bad/../foo", "/installation/repositories?per_page=1"):
                with self.subTest(path=path):
                    with self.assertRaises(ValueError):
                        reader.get(path)
            network.assert_not_called()

    def test_get_carries_auth_only_header_and_never_post(self):
        reader = probe.AppMetadataReadOnly("private-test-token")
        with patch("app_writer_provenance.urlopen") as net, \
             patch("app_writer_provenance.json.load", return_value=APP):
            self.assertEqual(reader.get("/apps/" + SLUG), APP)
            req = net.call_args.args[0]
            self.assertEqual(req.get_method(), "GET")
            self.assertEqual(req.get_header("Authorization"), "Bearer private-test-token")

    def test_network_or_permissions_error_stops_without_body(self):
        class Failing:
            def get(self, _):
                raise HTTPError("https://api.github.com", 403, "SECRET BODY", {}, None)
        result = probe.probe(Failing(), expected_app_id=APP_ID, expected_slug=SLUG,
                             minted_app_slug=SLUG, minted_installation_id=INSTALL)
        self.assertEqual(result["status"], "STOP")
        self.assertNotIn("SECRET", json.dumps(result))

    def test_probe_does_not_contact_api_when_identity_missing(self):
        class FailIfCalled:
            def get(self, _):
                raise AssertionError("network before trusted identity")
        result = probe.probe(FailIfCalled(), expected_app_id=None, expected_slug=SLUG,
                             minted_app_slug=SLUG, minted_installation_id=INSTALL)
        self.assertEqual(result["status"], "STOP")

    def test_valid_probe_reads_app_and_scoped_installation(self):
        paths = []
        class Reader:
            def get(self, path):
                paths.append(path)
                return APP if path == "/apps/" + SLUG else SCOPE
        result = probe.probe(Reader(), expected_app_id=APP_ID, expected_slug=SLUG,
                             minted_app_slug=SLUG, minted_installation_id=INSTALL)
        self.assertEqual(result["status"], "CREDENTIAL_PATH_OBSERVED")
        self.assertEqual(paths, ["/apps/" + SLUG,
                                 "/installation/repositories?per_page=100"])

    def test_owner_job_cannot_run_from_pr_or_schedule(self):
        from pathlib import Path
        workflow = (Path(__file__).resolve().parents[3]
                    / ".github/workflows/ai-eng-singleton-verify.yml").read_text()
        job = workflow.split("  owner-app-credential-probe:", 1)[1]
        self.assertIn("github.event_name == 'workflow_dispatch'", job)
        self.assertIn("github.actor == 'DaniilSydorenko'", job)
        self.assertIn("github.ref == 'refs/heads/main'", job)
        self.assertIn("vars.AI_ENG_WRITER_PROBE_ENABLED == 'true'", job)
        self.assertIn("environment: ai-eng-lease-owner", job)
        self.assertIn("permissions:\n      contents: read", job)
        self.assertIn("permission-contents: read", job)
        self.assertIn("persist-credentials: false", job)
        self.assertNotIn("api.cursor.com", job)
        self.assertNotIn("schedule:", workflow)

    def test_default_cli_without_secret_is_safe_stop(self):
        with patch.dict("os.environ", {}, clear=True), redirect_stdout(io.StringIO()) as out:
            self.assertEqual(probe.main(), 2)
            self.assertFalse(json.loads(out.getvalue())["cursor_launch_authorized"])


if __name__ == "__main__":
    unittest.main()
