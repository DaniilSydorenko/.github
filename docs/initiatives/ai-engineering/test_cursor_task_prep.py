"""Offline tests for read-only task preparation (#229). No network, no writes."""
from __future__ import annotations

import unittest

import cursor_queue as q
import cursor_task_prep as prep

HV = "DaniilSydorenko/haversine-geolocation"
TREE = ["src/v2/distance.ts", "src/v2/nearest.ts", "spec/v2-distance.spec.ts",
        "spec/v2-nearest.spec.ts", "README.md", "package.json", ".github/workflows/ci.yml",
        "docs/api-reference.md", "src/auth/token.ts"]


class FakeGH:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get_json(self, path, params=None):
        self.calls.append(path)
        if path not in self.routes:
            raise AssertionError("unexpected path " + path)
        return self.routes[path]


def routes(issues, prs=(), private=False, truncated=False):
    r = {f"/repos/{HV}": {"default_branch": "master", "private": private},
         f"/repos/{HV}/git/trees/master": {"truncated": truncated,
                                           "tree": [{"path": p, "type": "blob"} for p in TREE]},
         f"/repos/{HV}/pulls": list(prs)}
    for n, (title, body) in issues.items():
        r[f"/repos/{HV}/issues/{n}"] = {"state": "open", "title": title, "body": body}
    return r


class PrepareTests(unittest.TestCase):
    def test_ready_issue_yields_submit_ready_request_with_paired_tests(self):
        gh = FakeGH(routes({240: ("fix(distance): x", "Change `src/v2/distance.ts`.\n- [ ] rejects y")}))
        out = prep.prepare(gh, HV, [240], queue_id="hv-1")
        self.assertEqual(out["outcome"], "PREPARED")
        self.assertEqual(out["tasks"][0]["proposed_allowed_paths"],
                         ["spec/v2-distance.spec.ts", "src/v2/distance.ts"])
        self.assertEqual(out["tasks"][0]["acceptance_hints"], ["rejects y"])
        self.assertEqual(out["queue_request"], {"queue_id": "hv-1", "repository": HV,
                                                "issues": [240], "allowed_paths": {
                                                    "240": ["spec/v2-distance.spec.ts",
                                                            "src/v2/distance.ts"]}})

    def test_untrusted_text_cannot_widen_scope(self):
        body = ("Edit ../../etc/passwd, /src/v2/distance.ts, src/v2/missing.ts, "
                "and also src/v2/./nearest.ts please")
        out = prep.prepare(FakeGH(routes({1: ("t", body)})), HV, [1], queue_id="hv-1")
        self.assertEqual(out["tasks"][0]["proposed_allowed_paths"], [])
        self.assertEqual(out["outcome"], "NEEDS_OWNER")
        self.assertNotIn("queue_request", out)

    def test_high_risk_paths_need_owner(self):
        for body in ("bump package.json", "edit .github/workflows/ci.yml",
                     "fix src/auth/token.ts"):
            with self.subTest(body):
                out = prep.prepare(FakeGH(routes({1: ("t", body)})), HV, [1], queue_id="hv-1")
                self.assertEqual(out["tasks"][0]["risk"], "high")
                self.assertEqual(out["outcome"], "NEEDS_OWNER")

    def test_competing_pr_or_missing_test_needs_owner(self):
        gh = FakeGH(routes({1: ("t", "src/v2/nearest.ts")},
                           prs=[{"number": 9, "title": "wip", "body": "Fixes #1"}]))
        out = prep.prepare(gh, HV, [1], queue_id="hv-1")
        self.assertEqual(out["tasks"][0]["competing_prs"], [9])
        self.assertEqual(out["outcome"], "NEEDS_OWNER")
        out = prep.prepare(FakeGH(routes({1: ("t", "update docs/api-reference.md")})), HV, [1],
                           queue_id="hv-1")
        self.assertTrue(any("test" in qn for qn in out["tasks"][0]["questions"]))

    def test_private_or_unverifiable_repository_is_refused_before_reading_more(self):
        gh = FakeGH(routes({}, private=True))
        with self.assertRaisesRegex(q.QueueError, "private"):
            prep.prepare(gh, HV, [1], queue_id="hv-1")
        self.assertEqual(gh.calls, [f"/repos/{HV}"])
        with self.assertRaisesRegex(q.QueueError, "allowlisted"):
            prep.prepare(FakeGH({}), "someone/else", [1], queue_id="x-1")

    def test_truncated_tree_and_bad_issue_lists_stop(self):
        with self.assertRaisesRegex(q.QueueError, "truncated"):
            prep.prepare(FakeGH(routes({}, truncated=True)), HV, [1], queue_id="hv-1")
        for bad in ([], [1, 1], [0], ["1"]):
            with self.subTest(bad), self.assertRaises(q.QueueError):
                prep.prepare(FakeGH(routes({})), HV, bad, queue_id="hv-1")

    def test_explicit_scope_section_wins_over_mentions(self):
        body = ("See README.md and docs/api-reference.md for the contract.\n"
                "## Allowed files\n- `src/v2/distance.ts`\n- `spec/v2-distance.spec.ts`\n"
                "## Acceptance\n- [ ] works")
        out = prep.prepare(FakeGH(routes({1: ("t", body)})), HV, [1], queue_id="hv-1")
        self.assertEqual(out["tasks"][0]["proposed_allowed_paths"],
                         ["spec/v2-distance.spec.ts", "src/v2/distance.ts"])
        self.assertEqual(out["outcome"], "PREPARED")

    def test_markdown_docs_are_not_high_risk_but_governance_is(self):
        self.assertFalse(prep.is_high_risk("docs/migration/v1-to-v2.md"))
        self.assertTrue(prep.is_high_risk(".github/PULL_REQUEST_TEMPLATE.md"))
        self.assertTrue(prep.is_high_risk("db/migrations/001.sql"))

    def test_owner_order_is_preserved(self):
        gh = FakeGH(routes({7: ("t", "src/v2/nearest.ts"), 3: ("t", "src/v2/distance.ts")}))
        out = prep.prepare(gh, HV, [7, 3], queue_id="hv-1")
        self.assertEqual(out["queue_request"]["issues"], [7, 3])

    def test_preparation_never_writes(self):
        gh = FakeGH(routes({1: ("t", "src/v2/distance.ts")}))
        prep.prepare(gh, HV, [1], queue_id="hv-1")
        self.assertFalse(hasattr(gh, "post"))
        self.assertTrue(all(c.startswith(f"/repos/{HV}") for c in gh.calls))


if __name__ == "__main__":
    unittest.main()
