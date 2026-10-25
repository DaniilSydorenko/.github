"""Offline contract verification: no Cursor API calls, no model runs."""
import unittest

from cursor_pr_payload import PayloadError, existing_pr_payload


def sample(**changes):
    kwargs = {
        "request_id": "ladvero-issue-282-v1",
        "repository": "DaniilSydorenko/listing-kit",
        "pr_number": 284,
        "exact_pr_head": "a" * 40,
        "issue_number": 282,
        "model_id": "composer-2",
        "model_allowlist": frozenset({"composer-2"}),
    }
    kwargs.update(changes)
    return existing_pr_payload(**kwargs)


class PayloadTests(unittest.TestCase):
    def test_existing_pr_only(self):
        obj = sample()
        self.assertIs(obj["launch_allowed"], False)
        self.assertEqual(obj["status"], "PROPOSAL_ONLY")
        p = obj["payload"]
        self.assertEqual(p["repos"], [{"url": "https://github.com/DaniilSydorenko/listing-kit",
                                      "prUrl": "https://github.com/DaniilSydorenko/listing-kit/pull/284"}])
        self.assertTrue(p["workOnCurrentBranch"])
        self.assertFalse(p["autoCreatePR"])
        self.assertNotIn("startingRef", p["repos"][0])
        self.assertNotIn("envVars", p)
        self.assertNotIn("delivery", p)

    def test_stable_cursor_idempotency_key(self):
        self.assertEqual(sample()["payload"]["agentId"], sample()["payload"]["agentId"])
        self.assertNotEqual(sample()["payload"]["agentId"],
                            sample(request_id="ladvero-issue-283-v1")["payload"]["agentId"])
        self.assertTrue(sample()["payload"]["agentId"].startswith("bc-"))

    def test_not_permission_to_merge_or_deploy(self):
        text = sample()["payload"]["prompt"]["text"]
        self.assertIn("NEVER merge, deploy, release", text)
        self.assertIn("If it changed, or another writer is active: STOP", text)
        self.assertIn("mandatory exact-head CI", text)

    def test_model_must_be_owner_allowlisted(self):
        for models in (frozenset(), frozenset({"different"}), None, {"composer-2"}):
            with self.subTest(models=models), self.assertRaises(PayloadError):
                sample(model_allowlist=models)

    def test_missing_model_rejected(self):
        for model in ("", "arbitrary model with spaces", None):
            with self.subTest(model=model), self.assertRaises(PayloadError):
                sample(model_id=model)

    def test_no_invalid_repository_or_arbitrary_url(self):
        for repo in ("other.example/x", "../repo", "x/y/zz", "https://github.com/x/y"):
            with self.subTest(repo=repo), self.assertRaises(PayloadError):
                sample(repository=repo)

    def test_legitimate_dotgithub_repository_allowed(self):
        p = sample(repository="DaniilSydorenko/.github")["payload"]
        self.assertEqual(p["repos"][0]["url"], "https://github.com/DaniilSydorenko/.github")

    def test_no_invalid_pr_number(self):
        for n in (0, -1, True, "284"):
            with self.subTest(n=n), self.assertRaises(PayloadError):
                sample(pr_number=n)

    def test_no_invalid_issue_number(self):
        for n in (0, None, True, "282"):
            with self.subTest(n=n), self.assertRaises(PayloadError):
                sample(issue_number=n)

    def test_no_stale_looking_or_malformed_sha(self):
        for sha in ("", "abc", "a" * 39, "A" * 40, None):
            with self.subTest(sha=sha), self.assertRaises(PayloadError):
                sample(exact_pr_head=sha)

    def test_no_user_sourced_freeform_prompt_injection(self):
        # No arbitrary user-supplied prompt argument exists: bounded template only.
        self.assertEqual(set(sample().keys()),
                         {"status", "launch_allowed", "payload", "required_outside_this_function"})


if __name__ == "__main__":
    unittest.main()
