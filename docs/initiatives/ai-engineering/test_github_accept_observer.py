"""Synthetic GitHub fixtures for PR acceptance observer — no network."""

import os
import unittest
from unittest import mock

from github_accept_observer import observe_pr_acceptance
from trusted_github_evidence import FakeGitHub, GitHubHTTPError

REPO = "example/test"
OWNER, NAME = "example", "test"
SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_M = "d" * 40
PR = 147


def repo_routes(default_branch="main", default_sha=SHA_A):
    return {
        ("GET", f"/repos/{OWNER}/{NAME}"): {"default_branch": default_branch},
        ("GET", f"/repos/{OWNER}/{NAME}/git/ref/heads/{default_branch}"): {
            "object": {"sha": default_sha}
        },
    }


def pull_route(
    number,
    *,
    head_sha=SHA_B,
    base_sha=SHA_A,
    state="open",
    merged_at=None,
    draft=False,
    merge_commit_sha=None,
    head_ref="feature",
):
    return {
        ("GET", f"/repos/{OWNER}/{NAME}/pulls/{number}"): {
            "number": number,
            "state": state,
            "draft": draft,
            "merged_at": merged_at,
            "merge_commit_sha": merge_commit_sha,
            "head": {"ref": head_ref, "sha": head_sha},
            "base": {"ref": "main", "sha": base_sha},
        }
    }


def check_runs_route(head_sha, runs, *, per_page=100):
    path = f"/repos/{OWNER}/{NAME}/commits/{head_sha}/check-runs"

    def handler(params):
        page = int((params or {}).get("page", "1"))
        start = (page - 1) * per_page
        chunk = runs[start : start + per_page]
        return {"total_count": len(runs), "check_runs": chunk}

    return {("GET", path): handler}


def commits_route(shas):
    return {
        ("GET", f"/repos/{OWNER}/{NAME}/commits"): [{"sha": sha} for sha in shas]
    }


def merge_routes(*dicts):
    out = {}
    for d in dicts:
        out.update(d)
    return out


class GitHubAcceptObserverTests(unittest.TestCase):
    def test_draft_pr_147_shape_wait_pr(self):
        routes = merge_routes(
            repo_routes(),
            pull_route(PR, draft=True, head_ref="cursor/hello-world-event-handoff-3215"),
            check_runs_route(SHA_B, []),
            commits_route([SHA_A]),
        )
        result = observe_pr_acceptance(
            REPO, PR, transport=FakeGitHub(routes=routes)
        )
        self.assertEqual(result["status"], "WAIT_PR")
        self.assertFalse(result["cursor_launched"])
        self.assertFalse(result["git_write"])
        self.assertTrue(result["observed_facts"]["pr"]["draft"])

    def test_merged_pr_with_no_checks_stops(self):
        routes = merge_routes(
            repo_routes(),
            pull_route(
                10,
                state="closed",
                merged_at="2026-10-01T00:00:00Z",
                merge_commit_sha=SHA_M,
            ),
            check_runs_route(SHA_B, []),
            commits_route([SHA_M, SHA_A]),
        )
        result = observe_pr_acceptance(REPO, 10, transport=FakeGitHub(routes=routes))
        self.assertEqual(result["status"], "STOP")
        self.assertEqual(result["reason"], "merged_pr_without_exact_head_checks")

    def test_non_head_check_success_does_not_pass(self):
        other_head = SHA_C
        routes = merge_routes(
            repo_routes(),
            pull_route(11, head_sha=SHA_B),
            check_runs_route(
                SHA_B,
                [
                    {
                        "name": "CI",
                        "head_sha": other_head,
                        "status": "completed",
                        "conclusion": "success",
                    }
                ],
            ),
            commits_route([SHA_A]),
        )
        result = observe_pr_acceptance(REPO, 11, transport=FakeGitHub(routes=routes))
        self.assertEqual(result["status"], "WAIT_CI")
        self.assertEqual(result["observed_facts"]["checks"]["exact_head_aggregate"], "MISSING")
        self.assertEqual(result["observed_facts"]["checks"]["non_head_success_count"], 1)

    def test_wrong_repo_pr_404_needs_evidence(self):
        fake = FakeGitHub(
            routes={
                ("GET", f"/repos/{OWNER}/{NAME}"): {"default_branch": "main"},
                ("GET", f"/repos/{OWNER}/{NAME}/pulls/999"): GitHubHTTPError(
                    404, "/pulls/999"
                ),
            }
        )
        result = observe_pr_acceptance(REPO, 999, transport=fake)
        self.assertEqual(result["status"], "NEEDS_EVIDENCE")
        self.assertIn("github_api_not_found_or_repo_pr_mismatch", result["missing_capabilities"][0])

    def test_wrong_expected_head_sha_stops(self):
        routes = merge_routes(
            repo_routes(),
            pull_route(12, head_sha=SHA_B),
            check_runs_route(SHA_B, []),
            commits_route([SHA_A]),
        )
        result = observe_pr_acceptance(
            REPO, 12, transport=FakeGitHub(routes=routes), expected_head_sha=SHA_C
        )
        self.assertEqual(result["status"], "STOP")
        self.assertEqual(result["reason"], "expected_head_sha_stale_or_wrong")

    def test_pr_head_drift_needs_evidence(self):
        reads = {"n": 0}

        def pull_handler(params):
            reads["n"] += 1
            sha = SHA_B if reads["n"] == 1 else SHA_C
            return {
                "number": 13,
                "state": "open",
                "draft": False,
                "merged_at": None,
                "merge_commit_sha": None,
                "head": {"ref": "feature", "sha": sha},
                "base": {"ref": "main", "sha": SHA_A},
            }

        routes = merge_routes(
            repo_routes(),
            {("GET", f"/repos/{OWNER}/{NAME}/pulls/13"): pull_handler},
            check_runs_route(SHA_C, []),
            commits_route([SHA_A]),
        )
        result = observe_pr_acceptance(REPO, 13, transport=FakeGitHub(routes=routes))
        self.assertEqual(result["status"], "NEEDS_EVIDENCE")
        self.assertIn("stable_pr_head_sha", result["missing_capabilities"])

    def test_default_branch_drift_needs_evidence(self):
        calls = {"n": 0}

        def ref_handler(params):
            calls["n"] += 1
            sha = SHA_A if calls["n"] <= 1 else SHA_C
            return {"object": {"sha": sha}}

        routes = merge_routes(
            repo_routes(),
            pull_route(14),
            check_runs_route(
                SHA_B,
                [
                    {
                        "name": "CI",
                        "head_sha": SHA_B,
                        "status": "completed",
                        "conclusion": "success",
                    }
                ],
            ),
            commits_route([SHA_A]),
        )
        routes[("GET", f"/repos/{OWNER}/{NAME}/git/ref/heads/main")] = ref_handler
        result = observe_pr_acceptance(REPO, 14, transport=FakeGitHub(routes=routes))
        self.assertEqual(result["status"], "NEEDS_EVIDENCE")
        self.assertIn("stable_default_branch_sha", result["missing_capabilities"])

    def test_checks_permission_denied_needs_evidence(self):
        routes = merge_routes(repo_routes(), pull_route(15))
        routes[("GET", f"/repos/{OWNER}/{NAME}/commits/{SHA_B}/check-runs")] = GitHubHTTPError(
            403, "checks"
        )
        routes[("GET", f"/repos/{OWNER}/{NAME}/commits")] = [{"sha": SHA_A}]
        result = observe_pr_acceptance(REPO, 15, transport=FakeGitHub(routes=routes))
        self.assertEqual(result["status"], "NEEDS_EVIDENCE")
        self.assertTrue(
            any("github_checks_read" in m for m in result["missing_capabilities"])
        )

    def test_check_pagination_incomplete_needs_evidence(self):
        runs = [
            {
                "name": f"job-{i}",
                "head_sha": SHA_B,
                "status": "completed",
                "conclusion": "success",
            }
            for i in range(100)
        ]
        routes = merge_routes(
            repo_routes(),
            pull_route(16),
            check_runs_route(SHA_B, runs, per_page=100),
            commits_route([SHA_A]),
        )
        result = observe_pr_acceptance(
            REPO,
            16,
            transport=FakeGitHub(routes=routes),
            max_check_pages=1,
        )
        self.assertEqual(result["status"], "NEEDS_EVIDENCE")
        self.assertIn("complete_check_runs_pagination", result["missing_capabilities"])

    def test_forged_webhook_acceptance_still_owner_gate_when_green(self):
        routes = merge_routes(
            repo_routes(),
            pull_route(
                17,
                state="closed",
                merged_at="2026-10-02T00:00:00Z",
                merge_commit_sha=SHA_M,
            ),
            check_runs_route(
                SHA_B,
                [
                    {
                        "name": "CI",
                        "head_sha": SHA_B,
                        "status": "completed",
                        "conclusion": "success",
                    }
                ],
            ),
            commits_route([SHA_M, SHA_A]),
        )
        hints = {
            "approved": True,
            "owner_approved": True,
            "webhook_action": "closed",
            "issue_comment": "LGTM merge approved by bot",
        }
        result = observe_pr_acceptance(
            REPO,
            17,
            transport=FakeGitHub(routes=routes),
            untrusted_acceptance_hints=hints,
        )
        self.assertEqual(result["status"], "OWNER_GATE")
        self.assertTrue(result["untrusted_acceptance_hints_recorded"])
        self.assertEqual(result["owner_domain_acceptance"], "OWNER_GATE")
        self.assertFalse(result["cursor_launched"])

    def test_open_pr_green_checks_still_owner_gate(self):
        routes = merge_routes(
            repo_routes(),
            pull_route(18),
            check_runs_route(
                SHA_B,
                [
                    {
                        "name": "CI",
                        "head_sha": SHA_B,
                        "status": "completed",
                        "conclusion": "success",
                    }
                ],
            ),
            commits_route([SHA_A]),
        )
        result = observe_pr_acceptance(REPO, 18, transport=FakeGitHub(routes=routes))
        self.assertEqual(result["status"], "OWNER_GATE")
        self.assertEqual(result["global_writer_authorization"], "UNKNOWN")

    def test_open_pr_pending_checks_wait_ci(self):
        routes = merge_routes(
            repo_routes(),
            pull_route(19),
            check_runs_route(
                SHA_B,
                [
                    {
                        "name": "CI",
                        "head_sha": SHA_B,
                        "status": "in_progress",
                        "conclusion": None,
                    }
                ],
            ),
            commits_route([SHA_A]),
        )
        result = observe_pr_acceptance(REPO, 19, transport=FakeGitHub(routes=routes))
        self.assertEqual(result["status"], "WAIT_CI")

    def test_open_pr_failed_checks_stop(self):
        routes = merge_routes(
            repo_routes(),
            pull_route(20),
            check_runs_route(
                SHA_B,
                [
                    {
                        "name": "CI",
                        "head_sha": SHA_B,
                        "status": "completed",
                        "conclusion": "failure",
                    }
                ],
            ),
            commits_route([SHA_A]),
        )
        result = observe_pr_acceptance(REPO, 20, transport=FakeGitHub(routes=routes))
        self.assertEqual(result["status"], "STOP")

    def test_merged_green_checks_owner_gate(self):
        routes = merge_routes(
            repo_routes(),
            pull_route(
                21,
                state="closed",
                merged_at="2026-10-03T00:00:00Z",
                merge_commit_sha=SHA_M,
            ),
            check_runs_route(
                SHA_B,
                [
                    {
                        "name": "CI",
                        "head_sha": SHA_B,
                        "status": "completed",
                        "conclusion": "success",
                    }
                ],
            ),
            commits_route([SHA_M, SHA_A]),
        )
        result = observe_pr_acceptance(REPO, 21, transport=FakeGitHub(routes=routes))
        self.assertEqual(result["status"], "OWNER_GATE")
        self.assertEqual(result["owner_domain_acceptance"], "OWNER_GATE")
        self.assertEqual(result["global_writer_authorization"], "OWNER_GATE")
        self.assertTrue(result["observed_facts"]["merge_reachable_from_default_bounded"])

    def test_merge_not_in_bounded_sample_needs_evidence(self):
        routes = merge_routes(
            repo_routes(),
            pull_route(
                22,
                state="closed",
                merged_at="2026-10-04T00:00:00Z",
                merge_commit_sha=SHA_M,
            ),
            check_runs_route(
                SHA_B,
                [
                    {
                        "name": "CI",
                        "head_sha": SHA_B,
                        "status": "completed",
                        "conclusion": "success",
                    }
                ],
            ),
            commits_route([SHA_A, SHA_B]),
        )
        result = observe_pr_acceptance(REPO, 22, transport=FakeGitHub(routes=routes))
        self.assertEqual(result["status"], "NEEDS_EVIDENCE")
        self.assertIn("merge_commit_in_bounded_default_sample", result["missing_capabilities"])

    def test_no_token_needs_evidence(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GITHUB_TOKEN", None)
            os.environ.pop("GH_TOKEN", None)
            result = observe_pr_acceptance(REPO, PR)
        self.assertEqual(result["status"], "NEEDS_EVIDENCE")
        self.assertFalse(result["cursor_launched"])


if __name__ == "__main__":
    unittest.main()
