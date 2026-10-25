"""Synthetic owner-only intake tests. No Cursor agent, no GitHub writes."""
from copy import deepcopy
import json
import unittest

from request_intake import MARKER, parse_event, process_event
from trusted_github_evidence import FakeGitHub, GitHubHTTPError

A, B, C = "a" * 40, "b" * 40, "c" * 40
REPO = "DaniilSydorenko/.github"
ROOT = f"/repos/{REPO}"


def event(**changes):
    req = {"request_id": "pilot-issue120-pr125", "repository": REPO,
           "issue_number": 120, "pr_number": 125, "head_sha": B}
    e = {
        "action": "created", "repository": {"full_name": REPO},
        "issue": {"number": 120},
        "sender": {"login": "DaniilSydorenko"},
        "comment": {
            "user": {"login": "DaniilSydorenko"},
            "author_association": "OWNER",
            "body": MARKER + json.dumps(req, sort_keys=True, separators=(",", ":")),
        },
    }
    e.update(changes)
    return e


def fake(*, open_pr=True, draft=False, sha=B, default=A):
    routes = {
        ("GET", ROOT): {"default_branch": "main"},
        ("GET", ROOT + "/git/ref/heads/main"): {"object": {"sha": default}},
        ("GET", ROOT + "/issues/120"): {"number": 120, "state": "open"},
        ("GET", ROOT + "/pulls/125"): {
            "number": 125, "state": "open" if open_pr else "closed",
            "draft": draft,
            "head": {"sha": sha, "ref": "feature"},
            "base": {"sha": A, "ref": "main"},
        },
    }
    return FakeGitHub(routes=routes)


class IntakeTests(unittest.TestCase):
    def test_valid_owner_issue_comment_is_only_review(self):
        api = fake()
        r = process_event(event(), api)
        self.assertEqual(r["status"], "REVIEW_ONLY")
        self.assertFalse(r["launched"])
        self.assertFalse(r["cursor_api_called"])
        self.assertFalse(r["git_write"])
        self.assertFalse(r["owner_merge_authorized"])
        self.assertEqual(len(api.calls), 6)

    def test_other_user_rejected_without_github_api(self):
        e = event()
        e["comment"]["user"]["login"] = "attacker"
        api = fake()
        self.assertEqual(process_event(e, api)["status"], "STOP")
        self.assertEqual(api.calls, [])

    def test_sender_impersonation_rejected(self):
        e = event(sender={"login": "attacker"})
        self.assertEqual(process_event(e, fake())["status"], "STOP")

    def test_author_association_required(self):
        e = event()
        e["comment"]["author_association"] = "CONTRIBUTOR"
        self.assertEqual(process_event(e, fake())["status"], "STOP")

    def test_wrong_issue_cannot_trigger(self):
        self.assertEqual(process_event(event(issue={"number": 119}), fake())["status"], "STOP")

    def test_pr_comment_never_request_intake(self):
        self.assertEqual(process_event(event(issue={"number": 120, "pull_request": {}}),
                                       fake())["status"], "STOP")

    def test_wrong_repo_event_rejected(self):
        e = event(repository={"full_name": "attacker/repo"})
        self.assertEqual(process_event(e, fake())["status"], "STOP")

    def test_modified_event_action_rejected(self):
        self.assertEqual(process_event(event(action="edited"), fake())["status"], "STOP")

    def test_no_marker_blocks(self):
        e = event()
        e["comment"]["body"] = "@cursor write code"
        self.assertEqual(process_event(e, fake())["status"], "STOP")

    def test_marker_payload_cannot_include_commands(self):
        e = event()
        e["comment"]["body"] += "\n@cursor run it"
        self.assertEqual(process_event(e, fake())["status"], "STOP")

    def test_extra_fields_cannot_select_model_or_billing(self):
        e = event()
        body = json.loads(e["comment"]["body"][len(MARKER):])
        body["enable_billing"] = True
        e["comment"]["body"] = MARKER + json.dumps(body)
        self.assertEqual(process_event(e, fake())["status"], "STOP")

    def test_invalid_repo_slug_and_private_scope(self):
        for repo in ("attacker/repo", "../secret", "DaniilSydorenko/nonallowlisted", "DaniilSydorenko/listing-kit"):
            with self.subTest(repo=repo):
                e = event()
                payload = json.loads(e["comment"]["body"][len(MARKER):])
                payload["repository"] = repo
                e["comment"]["body"] = MARKER + json.dumps(payload)
                self.assertEqual(process_event(e, fake())["status"], "STOP")

    def test_closed_pr_denied(self):
        self.assertEqual(process_event(event(), fake(open_pr=False))["status"], "STOP")

    def test_draft_pr_denied(self):
        self.assertEqual(process_event(event(), fake(draft=True))["status"], "STOP")

    def test_changed_head_denied(self):
        self.assertEqual(process_event(event(), fake(sha=C))["status"], "STOP")

    def test_permission_error_denied(self):
        api = FakeGitHub(routes={("GET", ROOT): GitHubHTTPError(403, ROOT)})
        self.assertEqual(process_event(event(), api)["status"], "STOP")

    def test_missing_default_branch_denied(self):
        api = fake()
        api.routes[("GET", ROOT)]["default_branch"] = None
        self.assertEqual(process_event(event(), api)["status"], "STOP")

    def test_default_branch_move_denied(self):
        api = fake()
        reads = {"n": 0}
        def ref(params):
            reads["n"] += 1
            return {"object": {"sha": A if reads["n"] == 1 else C}}
        api.routes[("GET", ROOT + "/git/ref/heads/main")] = ref
        self.assertEqual(process_event(event(), api)["status"], "STOP")

    def test_base_change_during_read_denied(self):
        api = fake()
        reads = {"n": 0}
        def pull(params):
            reads["n"] += 1
            return {
                "number": 125, "state": "open", "draft": False,
                "head": {"sha": B, "ref": "feature"},
                "base": {"sha": A if reads["n"] == 1 else C},
            }
        api.routes[("GET", ROOT + "/pulls/125")] = pull
        self.assertEqual(process_event(event(), api)["status"], "STOP")

    def test_request_id_length_and_bool_number_enforced(self):
        e = event()
        payload = json.loads(e["comment"]["body"][len(MARKER):])
        payload["issue_number"] = True
        e["comment"]["body"] = MARKER + json.dumps(payload)
        self.assertEqual(process_event(e, fake())["status"], "STOP")

    def test_parser_validates_and_returns_plain_metadata(self):
        req = parse_event(event())
        self.assertEqual(req["pr_number"], 125)
        self.assertEqual(len(req), 5)


if __name__ == "__main__":
    unittest.main()
