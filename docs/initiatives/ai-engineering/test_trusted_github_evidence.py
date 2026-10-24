"""Synthetic GitHub API fixtures only — no network or real tokens."""

import os
import unittest
from unittest import mock

from trusted_github_evidence import (
    FakeGitHub,
    GitHubHTTPError,
    build_reconcile_observed,
    collect_task_evidence,
)

REPO = "example/test"
OWNER, NAME = "example", "test"
SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_FAKE = "f" * 40
ISSUE = 116


def repo_routes(default_branch="main", default_sha=SHA_A):
    return {
        ("GET", f"/repos/{OWNER}/{NAME}"): {"default_branch": default_branch},
        ("GET", f"/repos/{OWNER}/{NAME}/git/ref/heads/{default_branch}"): {
            "object": {"sha": default_sha}
        },
    }


def issue_route(state="open", body="", number=ISSUE):
    return {
        ("GET", f"/repos/{OWNER}/{NAME}/issues/{ISSUE}"): {
            "number": number,
            "state": state,
            "body": body,
        }
    }


def events_route(events, *, per_page=100):
    def handler(params):
        page = int((params or {}).get("page", "1"))
        start = (page - 1) * per_page
        chunk = events[start : start + per_page]
        return chunk

    return handler


def pull_routes(number, *, head_sha=SHA_B, state="open", merged_at=None, base="main", head_ref="feature"):
    routes = {
        ("GET", f"/repos/{OWNER}/{NAME}/pulls/{number}"): {
            "number": number,
            "state": state,
            "merged_at": merged_at,
            "head": {"ref": head_ref, "sha": head_sha},
            "base": {"ref": base},
        }
    }
    routes[("GET", f"/repos/{OWNER}/{NAME}/pulls/{number}/files")] = [
        {"filename": "docs/readme.md"}
    ]
    return routes


def commits_route(shas):
    return {
        ("GET", f"/repos/{OWNER}/{NAME}/commits"): [
            {"sha": sha} for sha in shas
        ]
    }


def merge_routes(*dicts):
    merged = {}
    for d in dicts:
        merged.update(d)
    return merged


class TrustedGitHubEvidenceTests(unittest.TestCase):
    def test_no_token_returns_needs_evidence(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GITHUB_TOKEN", None)
            os.environ.pop("GH_TOKEN", None)
            result = collect_task_evidence(REPO, ISSUE)
        self.assertEqual(result["status"], "NEEDS_EVIDENCE")
        self.assertTrue(result["missing_capabilities"])
        self.assertEqual(result["observed_facts"], {})

    def test_happy_path_observed_facts(self):
        routes = merge_routes(
            repo_routes(),
            issue_route(body="See #122"),
            {
                ("GET", f"/repos/{OWNER}/{NAME}/issues/{ISSUE}/events"): [
                    {
                        "event": "connected",
                        "source": {
                            "type": "issue",
                            "issue": {"number": 122, "pull_request": {}},
                        },
                    }
                ],
            },
            pull_routes(122),
            commits_route([SHA_A, SHA_B]),
        )
        fake = FakeGitHub(routes=routes)
        result = collect_task_evidence(REPO, ISSUE, transport=fake)
        self.assertEqual(result["status"], "OBSERVED")
        facts = result["observed_facts"]
        self.assertEqual(facts["issue_state"], "open")
        self.assertEqual(facts["default_sha"], SHA_A)
        self.assertEqual(len(facts["related_prs"]), 1)
        self.assertEqual(facts["related_prs"][0]["head_sha"], SHA_B)
        self.assertIn(122, facts["unverified_issue_text_pr_references"])

    def test_incomplete_event_pagination_is_partial(self):
        def events_pages(params):
            page = int((params or {}).get("page", "1"))
            if page <= 2:
                return [{"event": "commented"}] * 100
            return []

        routes = merge_routes(
            repo_routes(),
            issue_route(),
            {("GET", f"/repos/{OWNER}/{NAME}/issues/{ISSUE}/events"): events_pages},
            commits_route([SHA_A]),
        )
        result = collect_task_evidence(
            REPO, ISSUE, transport=FakeGitHub(routes=routes), max_event_pages=2
        )
        self.assertEqual(result["status"], "PARTIAL")
        self.assertFalse(result["observed_facts"]["issue_events_pagination_complete"])

    def test_missing_pr_head_sha(self):
        routes = merge_routes(
            repo_routes(),
            issue_route(),
            {("GET", f"/repos/{OWNER}/{NAME}/issues/{ISSUE}/events"): []},
            pull_routes(50, head_sha=None),
            commits_route([SHA_A]),
        )
        routes[("GET", f"/repos/{OWNER}/{NAME}/pulls/50")]["head"]["sha"] = None
        result = collect_task_evidence(
            REPO, ISSUE, transport=FakeGitHub(routes=routes), explicit_pr_numbers=[50]
        )
        pr = result["observed_facts"]["related_prs"][0]
        self.assertFalse(pr["head_sha_observed"])
        self.assertIsNone(pr["head_sha"])

    def test_default_sha_changed_mid_collection(self):
        calls = {"n": 0}

        def ref_handler(params):
            calls["n"] += 1
            sha = SHA_A if calls["n"] == 1 else SHA_B
            return {"object": {"sha": sha}}

        routes = merge_routes(repo_routes(), issue_route(), commits_route([SHA_B]))
        routes[("GET", f"/repos/{OWNER}/{NAME}/git/ref/heads/main")] = ref_handler
        routes[("GET", f"/repos/{OWNER}/{NAME}/issues/{ISSUE}/events")] = []
        result = collect_task_evidence(REPO, ISSUE, transport=FakeGitHub(routes=routes))
        self.assertEqual(result["observed_facts"]["default_sha"], SHA_B)
        self.assertIn("Default branch SHA changed during collection", result["warnings"])

    def test_pr_head_changed_during_collection(self):
        reads = {"n": 0}

        def pull_handler(params):
            reads["n"] += 1
            sha = SHA_B if reads["n"] == 1 else SHA_FAKE
            return {
                "number": 9,
                "state": "open",
                "merged_at": None,
                "head": {"ref": "feature", "sha": sha},
                "base": {"ref": "main"},
            }

        routes = merge_routes(
            repo_routes(),
            issue_route(),
            {("GET", f"/repos/{OWNER}/{NAME}/issues/{ISSUE}/events"): []},
            {("GET", f"/repos/{OWNER}/{NAME}/pulls/9/files"): [{"filename": "x.txt"}]},
            commits_route([SHA_A]),
        )
        routes[("GET", f"/repos/{OWNER}/{NAME}/pulls/9")] = pull_handler
        result = collect_task_evidence(
            REPO, ISSUE, transport=FakeGitHub(routes=routes), explicit_pr_numbers=[9]
        )
        self.assertEqual(result["observed_facts"]["related_prs"][0]["head_sha"], SHA_FAKE)
        self.assertTrue(any("HEAD changed" in w for w in result["warnings"]))

    def test_pr_merged_during_collection(self):
        reads = {"n": 0}

        def pull_handler(params):
            reads["n"] += 1
            return {
                "number": 7,
                "state": "open" if reads["n"] == 1 else "closed",
                "merged_at": None if reads["n"] == 1 else "2026-01-01T00:00:00Z",
                "head": {"ref": "feature", "sha": SHA_B},
                "base": {"ref": "main"},
            }

        routes = merge_routes(
            repo_routes(),
            issue_route(),
            {("GET", f"/repos/{OWNER}/{NAME}/issues/{ISSUE}/events"): []},
            {("GET", f"/repos/{OWNER}/{NAME}/pulls/7/files"): [{"filename": "y.txt"}]},
            commits_route([SHA_A]),
        )
        routes[("GET", f"/repos/{OWNER}/{NAME}/pulls/7")] = pull_handler
        result = collect_task_evidence(
            REPO, ISSUE, transport=FakeGitHub(routes=routes), explicit_pr_numbers=[7]
        )
        pr = result["observed_facts"]["related_prs"][0]
        self.assertTrue(pr["merged"])
        self.assertTrue(any("merged during collection" in w for w in result["warnings"]))

    def test_unrelated_linked_pr_still_observed_not_blocking(self):
        """Collector lists task-local PRs; unrelated relation is a reviewer assertion."""
        routes = merge_routes(
            repo_routes(),
            issue_route(),
            {
                ("GET", f"/repos/{OWNER}/{NAME}/issues/{ISSUE}/events"): [
                    {
                        "event": "cross-referenced",
                        "source": {
                            "type": "issue",
                            "issue": {"number": 999, "pull_request": {}},
                        },
                    }
                ]
            },
            pull_routes(999, head_sha=SHA_FAKE),
            commits_route([SHA_A]),
        )
        result = collect_task_evidence(REPO, ISSUE, transport=FakeGitHub(routes=routes))
        self.assertEqual(result["status"], "OBSERVED")
        self.assertEqual(result["observed_facts"]["related_prs"][0]["number"], 999)
        self.assertIn("related_prs[].relation", result["reviewer_assertions_required"])

    def test_fabricated_accepted_sha_in_issue_body_not_observed_as_accepted(self):
        body = f"Merged proof: {SHA_FAKE} and https://github.com/{REPO}/pull/1"
        routes = merge_routes(
            repo_routes(),
            issue_route(body=body),
            {("GET", f"/repos/{OWNER}/{NAME}/issues/{ISSUE}/events"): []},
            commits_route([SHA_A]),
        )
        result = collect_task_evidence(REPO, ISSUE, transport=FakeGitHub(routes=routes))
        facts = result["observed_facts"]
        self.assertIn(SHA_FAKE, body)
        self.assertNotIn(SHA_FAKE, facts["default_branch_recent_commit_shas"])
        self.assertIsNone(facts["accepted_shas"])
        observed = build_reconcile_observed(result)
        self.assertEqual(observed["accepted_shas"], [])

    def test_repo_issue_mismatch_404(self):
        fake = FakeGitHub(
            routes=merge_routes(
                repo_routes(),
                {("GET", f"/repos/{OWNER}/{NAME}/issues/{ISSUE}"): GitHubHTTPError(404, "issue")},
            )
        )
        result = collect_task_evidence(REPO, ISSUE, transport=fake)
        self.assertEqual(result["status"], "NEEDS_EVIDENCE")
        self.assertIn("github_api_not_found_or_repo_issue_mismatch", result["missing_capabilities"][0])

    def test_rate_limit_429(self):
        fake = FakeGitHub(
            routes={
                ("GET", f"/repos/{OWNER}/{NAME}"): GitHubHTTPError(429, "/repos", "rate limit")
            }
        )
        result = collect_task_evidence(REPO, ISSUE, transport=fake)
        self.assertEqual(result["status"], "NEEDS_EVIDENCE")
        self.assertIn("github_api_rate_limit_or_permission_denied", result["missing_capabilities"][0])

    def test_permission_denied_403(self):
        fake = FakeGitHub(
            routes={
                ("GET", f"/repos/{OWNER}/{NAME}"): GitHubHTTPError(403, "/repos", " forbidden")
            }
        )
        result = collect_task_evidence(REPO, ISSUE, transport=fake)
        self.assertEqual(result["status"], "NEEDS_EVIDENCE")
        self.assertIn("github_api_rate_limit_or_permission_denied", result["missing_capabilities"][0])

    def test_incomplete_pull_files_pagination_partial(self):
        def files_handler(params):
            page = int((params or {}).get("page", "1"))
            if page == 1:
                return [{"filename": f"path/{i}.md"} for i in range(100)]
            return [{"filename": "extra.md"}]

        routes = merge_routes(
            repo_routes(),
            issue_route(),
            {("GET", f"/repos/{OWNER}/{NAME}/issues/{ISSUE}/events"): []},
            pull_routes(3),
            commits_route([SHA_A]),
        )
        routes[("GET", f"/repos/{OWNER}/{NAME}/pulls/3/files")] = files_handler
        result = collect_task_evidence(
            REPO,
            ISSUE,
            transport=FakeGitHub(routes=routes),
            explicit_pr_numbers=[3],
            max_file_pages=1,
        )
        self.assertEqual(result["status"], "PARTIAL")
        self.assertFalse(result["observed_facts"]["related_prs_files_pagination_complete"])

    def test_build_reconcile_observed_omits_inventory_complete(self):
        routes = merge_routes(
            repo_routes(),
            issue_route(),
            {("GET", f"/repos/{OWNER}/{NAME}/issues/{ISSUE}/events"): []},
            commits_route([SHA_A]),
        )
        result = collect_task_evidence(REPO, ISSUE, transport=FakeGitHub(routes=routes))
        observed = build_reconcile_observed(result)
        self.assertIsNone(observed["related_inventory_complete"])
        self.assertEqual(observed["default_sha"], SHA_A)


if __name__ == "__main__":
    unittest.main()
