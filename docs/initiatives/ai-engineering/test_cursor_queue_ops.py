"""Offline tests: queue operations wired into the protected cycle (#226)."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import cursor_queue as q
import cursor_queue_ops as ops
import cursor_tasks
from test_cursor_queue import AUTH, HV, LK as PRIVATE, TreeRef, spec

LK = HV  # queue targets must be public while the control plane is public


class FakeGH:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get_json(self, path, params=None):
        self.calls.append(path)
        if path not in self.routes:
            raise AssertionError("unexpected path " + path)
        return self.routes[path]


def lk_routes(**over):
    routes = {
        f"/repos/{LK}": {"default_branch": "main", "private": False},
        f"/repos/{LK}/rules/branches/main": [
            {"type": "pull_request"},
            {"type": "required_status_checks",
             "parameters": {"required_status_checks": [{"context": "quality"},
                                                       {"context": "Gitleaks"}]}}],
        f"/repos/{LK}/pulls": [{"number": 40, "title": "fix #17", "body": "unrelated #170"}],
        **{f"/repos/{LK}/issues/{n}": {"state": "open"} for n in (1, 7, 5)},
    }
    routes.update(over)
    return routes


REQUEST = {"queue_id": "lk-batch-1", "repository": LK, "issues": [1, 7, 5],
           "allowed_paths": {"1": ["src/a.ts"], "7": ["src/b.ts"], "5": ["src/c.ts"]}}


class BuildSpecTests(unittest.TestCase):
    def test_trusted_fields_come_from_github_not_the_request(self):
        s = ops.build_spec(FakeGH(lk_routes()), dict(REQUEST))
        self.assertEqual(s["default_branch"], "main")
        self.assertEqual([t["issue"] for t in s["tasks"]], [1, 7, 5])
        self.assertEqual(s["tasks"][0]["required_checks"], ["Gitleaks", "quality"])
        self.assertIs(s["accept_subagent_risk"], False)  # default false
        self.assertEqual(s["max_launches"], 3)
        with self.assertRaises(q.QueueError):  # caller cannot inject trusted fields
            ops.build_spec(FakeGH(lk_routes()), {**REQUEST, "required_checks": ["x"]})

    def test_missing_required_checks_fail_closed(self):
        with self.assertRaisesRegex(q.QueueError, "required checks"):
            ops.build_spec(FakeGH(lk_routes(**{f"/repos/{LK}/rules/branches/main": []})),
                           dict(REQUEST))

    def test_closed_issue_pr_or_competing_pr_blocks(self):
        cases = {
            "not open": {f"/repos/{LK}/issues/7": {"state": "closed"}},
            "not an issue": {f"/repos/{LK}/issues/7": {"state": "open", "pull_request": {}}},
            "open PR": {f"/repos/{LK}/pulls": [{"number": 41, "title": "x", "body": "Closes #5"}]},
        }
        for reason, over in cases.items():
            with self.subTest(reason), self.assertRaisesRegex(q.QueueError, reason):
                ops.build_spec(FakeGH(lk_routes(**over)), dict(REQUEST))

    def test_private_repository_is_refused_before_any_read(self):
        gh = FakeGH({})
        for repo in (PRIVATE, "DaniilSydorenko/engineering-handbook"):
            with self.subTest(repo), self.assertRaisesRegex(q.QueueError, "private"):
                ops.build_spec(gh, {**REQUEST, "repository": repo})
        self.assertEqual(gh.calls, [])  # nothing about the target was fetched or logged
        routes = lk_routes(**{f"/repos/{LK}": {"default_branch": "main", "private": True}})
        with self.assertRaisesRegex(q.QueueError, "public"):
            ops.build_spec(FakeGH(routes), dict(REQUEST))

    def test_request_shape_and_repository(self):
        for bad in ({**REQUEST, "repository": "someone/else"},
                    {**REQUEST, "allowed_paths": {"1": ["a"]}},
                    {**REQUEST, "issues": [1, "7"]}, {**REQUEST, "model": "x"}):
            with self.subTest(bad), self.assertRaises(q.QueueError):
                ops.build_spec(FakeGH(lk_routes()), bad)


class DispatchGateTests(unittest.TestCase):
    def setUp(self):
        self.store = TreeRef()
        self.doc = q.submit(self.store, spec(issues=(1, 7, 5), max_launches=2),
                            expected_queue_revision=None, **AUTH)
        self.tasks = {t.issue: t for t in q.validate_document(self.doc)}

    def progress(self, issue, *states, pr=None):
        for st in states:
            ev = {"pr_number": pr} if st == "DONE" else {}
            self.doc = q.set_progress(self.store, issue, st, ev,
                                      expected_spec_digest=self.doc["spec_digest"])

    def test_only_the_head_may_dispatch_in_owner_order(self):
        self.assertIsNone(ops.dispatch_gate(self.doc, self.tasks[1]))
        self.assertEqual(ops.dispatch_gate(self.doc, self.tasks[7]), "task_is_not_queue_head")
        self.assertIsNone(ops.previous_pr(self.doc))  # first task = bootstrap
        self.progress(1, "RUNNING")
        self.assertEqual(ops.dispatch_gate(self.doc, self.tasks[1]), "queue_head_running")
        self.progress(1, "DONE", pr=301)
        self.assertIsNone(ops.dispatch_gate(self.doc, self.tasks[7]))
        self.assertEqual(ops.previous_pr(self.doc), 301)

    def test_launch_limit_and_blocked_head(self):
        self.progress(1, "RUNNING", "DONE", pr=301)
        self.progress(7, "RUNNING", "DONE", pr=302)
        self.assertEqual(ops.dispatch_gate(self.doc, self.tasks[5]), "queue_launch_limit_reached")
        store = TreeRef()
        doc = q.submit(store, spec(issues=(1, 7)), expected_queue_revision=None, **AUTH)
        doc = q.set_progress(store, 1, "BLOCKED", {}, expected_spec_digest=doc["spec_digest"])
        tasks = {t.issue: t for t in q.validate_document(doc)}
        self.assertEqual(ops.dispatch_gate(doc, tasks[7]), "task_is_not_queue_head")
        self.assertEqual(ops.dispatch_gate(doc, tasks[1]), "queue_head_blocked")

    def test_binding_carries_queue_risk_decision(self):
        b = ops.binding(self.doc, self.tasks[1])
        self.assertEqual(b, {"spec_digest": self.doc["spec_digest"], "repository": LK,
                             "issue": 1, "accept_subagent_risk": False})


class SyncProgressTests(unittest.TestCase):
    def test_dispatch_then_release_records_running_then_done(self):
        from github_ref_lease import Controller
        store = TreeRef()
        doc = q.submit(store, spec(issues=(1, 7)), expected_queue_revision=None, **AUTH)
        issue_url = f"https://github.com/{LK}/issues/1"
        gate = Controller(store)
        gate.acquire("seq-0000000000000001", issue_url)
        doc = ops.sync_progress(store, doc, {"lifecycle_steps": [{"outcome": "DISPATCH_ATTEMPTED"}]},
                                workflow_run_id="1")
        self.assertEqual(doc["progress"]["1"]["state"], "RUNNING")
        self.assertEqual(doc["progress"]["1"]["evidence"]["request_id"], "seq-0000000000000001")
        # Simulate the verified release (the lifecycle itself is covered elsewhere).
        store.state = {**store.state, "phase": "IDLE", "request_id": None, "agent_id": None,
                       "run_id": None, "pr_url": None, "source_issue_url": None}
        done = ops.sync_progress(store, doc, {
            "lifecycle_steps": [{"outcome": "RELEASED"}],
            "pr": f"https://github.com/{LK}/pull/301",
            "acceptance": {"exact_head": "e" * 40, "merge_sha": "f" * 40}}, workflow_run_id="2")
        self.assertEqual(done["progress"]["1"], {"state": "DONE", "evidence": {
            "pr_number": 301, "exact_head": "e" * 40, "merge_sha": "f" * 40,
            "workflow_run_id": "2"}})
        self.assertEqual(q.next_task(done).issue, 7)


class CycleQueueWiringTests(unittest.TestCase):
    def tearDown(self):
        cursor_tasks.deactivate()

    def test_new_dispatch_requires_a_queue(self):
        import cursor_delivery_cycle as cycle
        from cursor_protected_dispatch import ProtectedCursorContext
        ctx = ProtectedCursorContext("DaniilSydorenko/.github", "DaniilSydorenko", "refs/heads/main",
                                     "workflow_dispatch", "1", "cursor-managed-delivery", 235, "9",
                                     False)
        with patch("cursor_protected_dispatch.protected_context_from_env", lambda: ctx), \
                patch.object(cycle, "protected_context_from_env", lambda: ctx):
            d = cycle._live_dispatch(FakeGH({}), None, bootstrap=True, previous_pr=None)
            self.assertEqual(d({"phase": "IDLE"}), {"decision": "STOP", "reason": "no_queue_submitted"})

    def test_loaded_queue_replaces_static_registry_and_selects_head(self):
        import cursor_delivery_cycle as cycle
        store = TreeRef()
        q.submit(store, spec(issues=(7, 1)), expected_queue_revision=None, **AUTH)
        with patch.dict("os.environ", {}, clear=True):
            doc = cycle._load_queue(store)
            import os
            self.assertEqual(os.environ["AI_ENG_OWNER_GO_ISSUE"], "7")
        self.assertEqual([t.issue for t in cursor_tasks.registry()], [7, 1])
        self.assertIsNone(cursor_tasks.task_for("DaniilSydorenko/haversine-geolocation", 235))
        self.assertEqual(cycle._queue_summary(doc)["next"], 7)

    def test_malformed_queue_stops_the_cycle(self):
        import cursor_delivery_cycle as cycle
        store = TreeRef()
        store.blobs[store.tree] = {q.QUEUE_FILE: b"{broken"}
        with patch.object(cycle, "_live", lambda: (store, FakeGH({}), None)), \
                patch.dict("os.environ", {}, clear=True):
            self.assertEqual(cycle.main(["advance"]), 3)
        self.assertEqual(store.state["phase"], "IDLE")

    def test_submit_cli_requires_owner_workflow_and_writes_queue(self):
        import cursor_delivery_cycle as cycle
        store = TreeRef()
        env = {"GITHUB_REPOSITORY": "DaniilSydorenko/.github", "GITHUB_ACTOR": "DaniilSydorenko",
               "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": "workflow_dispatch",
               "GITHUB_RUN_ATTEMPT": "1", "GITHUB_RUN_ID": "46200000009",
               "AI_ENG_APPROVED_OPERATION": "cursor-managed-delivery"}
        argv = ["submit-queue", "--request-json", json.dumps(REQUEST),
                "--expected-queue-revision", "none"]
        with patch.object(cycle, "_live", lambda: (store, FakeGH(lk_routes()), None)):
            with patch.dict("os.environ", {**env, "GITHUB_ACTOR": "someone"}, clear=True):
                self.assertEqual(cycle.main(argv), 3)
            self.assertIsNone(q.load(store, store.read()))
            with patch.dict("os.environ", env, clear=True):
                self.assertEqual(cycle.main(argv), 0)
        doc = q.load(store, store.read())
        self.assertEqual(doc["authorization"]["workflow_run_id"], "46200000009")
        self.assertEqual([t["issue"] for t in doc["spec"]["tasks"]], [1, 7, 5])


if __name__ == "__main__":
    unittest.main()
