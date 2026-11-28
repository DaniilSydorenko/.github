"""Offline tests for the durable ordered task queue (#226). No network, no POST."""
from __future__ import annotations

import copy
import hashlib
import json
import threading
import unittest
from unittest.mock import patch

import cursor_queue as q
from cursor_tasks import DEFAULT_MODEL, TASKS
from github_ref_lease import Controller, LeaseError, RefConflict, Snapshot, fingerprint, initial_state

LK = "DaniilSydorenko/listing-kit"
HV = "DaniilSydorenko/haversine-geolocation"


class TreeRef:
    """GitHub ref + tree simulation: non-forced CAS, trees are content-addressed."""

    def __init__(self, state=None):
        self._mutex = threading.Lock()
        self.sha = "a" * 40
        self.state = state or initial_state()
        self.blobs: dict[str, dict[str, bytes]] = {"b" * 40: {}}
        self.tree = "b" * 40
        self.race = None  # callable run once just before the next advance

    def read(self):
        with self._mutex:
            return Snapshot(self.sha, self.tree, copy.deepcopy(self.state))

    def read_file(self, tree, name):
        return self.blobs[tree].get(name)

    def write_tree(self, base_tree, name, content):
        files = {**self.blobs[base_tree], name: bytes(content)}
        sha = hashlib.sha1(json.dumps({k: v.decode() for k, v in sorted(files.items())})
                           .encode()).hexdigest()
        self.blobs[sha] = files
        return sha

    def advance(self, observed, state, tree=None):
        if self.race:
            race, self.race = self.race, None
            race()
        with self._mutex:
            if self.sha != observed.sha:
                raise RefConflict("GitHub rejected non-fast-forward")
            if state["revision"] != observed.state["revision"] + 1:
                raise LeaseError("non-monotonic revision")
            if tree is not None and {**state, "revision": 0} != {**observed.state, "revision": 0}:
                raise LeaseError("queue write must not change the lease state")
            self.sha = format(int(self.sha, 16) + 1, "040x")
            self.state = copy.deepcopy(state)
            self.tree = tree or observed.tree
            return self.sha


def spec(repo=LK, issues=(1, 7, 5), **kw):
    s = {"schema": 1, "queue_id": "lk-first-batch", "repository": repo, "default_branch": "main",
         "model": DEFAULT_MODEL, "accept_subagent_risk": False, "max_launches": len(issues),
         "tasks": [{"issue": n, "order": i + 1, "allowed_paths": [f"src/f{n}.ts", f"test/f{n}.spec.ts"],
                    "required_checks": ["ci"]} for i, n in enumerate(issues)]}
    s.update(kw)
    return s


AUTH = dict(workflow_run_id="46200000001", actor="DaniilSydorenko")


class QueueSpecTests(unittest.TestCase):
    def test_arbitrary_owner_order_is_preserved(self):
        store = TreeRef()
        doc = q.submit(store, spec(issues=(1, 7, 5)), expected_queue_revision=None, **AUTH)
        self.assertEqual([t.issue for t in q.validate_document(doc)], [1, 7, 5])
        self.assertEqual(q.next_task(doc).issue, 1)

    def test_rejections(self):
        bad = {
            "duplicate": spec(issues=(1, 7, 1)),
            "repository": spec(repo="someone/else"),
            "issue_zero": spec(issues=(0, 7)),
            "issue_type": spec(issues=("1", 7)),
            "abs_path": {**spec(), "tasks": [{**spec()["tasks"][0], "allowed_paths": ["/etc/x"]}]},
            "dotdot": {**spec(), "tasks": [{**spec()["tasks"][0], "allowed_paths": ["a/../b"]}]},
            "no_checks": {**spec(), "tasks": [{**spec()["tasks"][0], "required_checks": []}]},
            "model": spec(model="gpt-5.5"),
            "limits": spec(max_launches=0),
            "too_many_launches": spec(max_launches=9),
            "extra_key": {**spec(), "admin": True},
            "order_gap": {**spec(), "tasks": [{**t, "order": t["order"] * 2} for t in spec()["tasks"]]},
            "risk_not_bool": spec(accept_subagent_risk="yes"),
        }
        for name, s in bad.items():
            with self.subTest(name), self.assertRaises(q.QueueError):
                q.validate_spec(s)

    def test_dependency_must_be_an_earlier_task(self):
        s = spec(issues=(1, 7, 5))
        s["tasks"][2]["dependencies"] = [7]
        q.validate_spec(s)
        for deps in ([5], [9], [1, 5]):
            s2 = copy.deepcopy(s)
            s2["tasks"][1]["dependencies"] = deps
            with self.subTest(deps), self.assertRaises(q.QueueError):
                q.validate_spec(s2)

    def test_cross_repository_issue_numbers_do_not_collide(self):
        from sequential_handoff import request_id_for_issue
        self.assertNotEqual(request_id_for_issue(LK, 235), request_id_for_issue(HV, 235))
        a, b = q.validate_spec(spec(repo=LK, issues=(235,))), q.validate_spec(spec(repo=HV, issues=(235,)))
        self.assertNotEqual((a[0].repository, a[0].issue), (b[0].repository, b[0].issue))


class QueueStorageTests(unittest.TestCase):
    def test_submit_requires_idle_lease_and_exact_revision(self):
        store = TreeRef()
        q.submit(store, spec(), expected_queue_revision=None, **AUTH)
        with self.assertRaisesRegex(q.QueueError, "stale"):
            q.submit(store, spec(issues=(2,)), expected_queue_revision=None, **AUTH)
        doc = q.submit(store, spec(issues=(2,)), expected_queue_revision=1, **AUTH)
        self.assertEqual(doc["revision"], 2)
        Controller(store).acquire("req-00000001", "https://github.com/DaniilSydorenko/listing-kit/issues/2")
        with self.assertRaisesRegex(q.QueueError, "IDLE"):
            q.submit(store, spec(issues=(3,)), expected_queue_revision=2, **AUTH)

    def test_queue_write_preserves_lease_and_replay_ledger(self):
        state = {**initial_state(), "revision": 41,
                 "consumed_request_hashes": [fingerprint("req-old-0001"), fingerprint("req-old-0002")]}
        store = TreeRef(state)
        q.submit(store, spec(), expected_queue_revision=None, **AUTH)
        self.assertEqual(store.state["revision"], 42)
        self.assertEqual(store.state["consumed_request_hashes"], state["consumed_request_hashes"])
        self.assertEqual(store.state["phase"], "IDLE")

    def test_every_lease_transition_preserves_the_queue(self):
        store = TreeRef()
        doc = q.submit(store, spec(), expected_queue_revision=None, **AUTH)
        gate, rid = Controller(store), "req-00000001"
        issue = "https://github.com/DaniilSydorenko/listing-kit/issues/1"
        gate.acquire(rid, issue)
        gate.transition(rid, "RESERVED", "DISPATCHING")
        gate.transition(rid, "DISPATCHING", "RUNNING", run_id="run-1")
        gate.transition(rid, "RUNNING", "VERIFYING")
        gate.bind_generated_pr(rid, expected_issue_url=issue,
                               generated_pr_url="https://github.com/DaniilSydorenko/listing-kit/pull/9")
        gate.release_verified(rid, provider_terminal=True, integration_accepted=True,
                              manual_approval=True)
        self.assertEqual(store.state["phase"], "IDLE")
        self.assertEqual(q.load(store, store.read()), doc)  # restart: re-read is identical

    def test_progress_keeps_authorization_and_is_idempotent(self):
        store = TreeRef()
        doc = q.submit(store, spec(), expected_queue_revision=None, **AUTH)
        d = doc["spec_digest"]
        r = q.set_progress(store, 1, "RUNNING", {"request_id": "seq-x"}, expected_spec_digest=d)
        self.assertEqual(r["authorization"], doc["authorization"])
        self.assertIs(q.set_progress(store, 1, "RUNNING", {}, expected_spec_digest=d)["revision"],
                      r["revision"])  # workflow retry: no second write
        q.set_progress(store, 1, "DONE", {"merge": "0" * 40}, expected_spec_digest=d)
        self.assertEqual(q.next_task(q.load(store, store.read())).issue, 7)
        with self.assertRaisesRegex(q.QueueError, "illegal"):
            q.set_progress(store, 1, "RUNNING", {}, expected_spec_digest=d)

    def test_progress_refuses_a_changed_spec(self):
        store = TreeRef()
        doc = q.submit(store, spec(), expected_queue_revision=None, **AUTH)
        q.submit(store, spec(issues=(1, 5)), expected_queue_revision=1, **AUTH)
        with self.assertRaisesRegex(q.QueueError, "spec changed"):
            q.set_progress(store, 1, "RUNNING", {}, expected_spec_digest=doc["spec_digest"])

    def test_progress_rereads_after_cas_conflict_without_overwrite(self):
        store = TreeRef()
        doc = q.submit(store, spec(), expected_queue_revision=None, **AUTH)
        store.race = lambda: Controller(store).acquire(
            "req-00000001", "https://github.com/DaniilSydorenko/listing-kit/issues/1")
        out = q.set_progress(store, 1, "RUNNING", {}, expected_spec_digest=doc["spec_digest"])
        self.assertEqual(store.state["phase"], "RESERVED")  # the racing lease write survived
        self.assertEqual(out["progress"]["1"]["state"], "RUNNING")

    def test_reorder_moves_only_pending_and_needs_new_authorization(self):
        store = TreeRef()
        doc = q.submit(store, spec(issues=(1, 7, 5)), expected_queue_revision=None, **AUTH)
        q.set_progress(store, 1, "RUNNING", {}, expected_spec_digest=doc["spec_digest"])
        q.set_progress(store, 1, "DONE", {}, expected_spec_digest=doc["spec_digest"])
        with self.assertRaisesRegex(q.QueueError, "only PENDING"):
            q.reorder(store, [7, 1, 5], expected_queue_revision=3, **AUTH)
        new = q.reorder(store, [1, 5, 7], workflow_run_id="46200000002", actor="DaniilSydorenko",
                        expected_queue_revision=3)
        self.assertNotEqual(new["spec_digest"], doc["spec_digest"])
        self.assertEqual(new["authorization"]["workflow_run_id"], "46200000002")
        self.assertEqual(new["authorization"]["spec_digest"], new["spec_digest"])
        self.assertEqual(new["progress"]["1"]["state"], "DONE")
        with self.assertRaisesRegex(q.QueueError, "stale"):
            q.reorder(store, [1, 7, 5], expected_queue_revision=3, **AUTH)

    def test_reordered_spec_cannot_inherit_old_authorization(self):
        store = TreeRef()
        doc = q.submit(store, spec(issues=(1, 7, 5)), expected_queue_revision=None, **AUTH)
        forged = copy.deepcopy(doc)
        forged["spec"]["tasks"] = [{**t, "order": i + 1} for i, t in
                                   enumerate(reversed(forged["spec"]["tasks"]))]
        forged["spec_digest"] = q.spec_digest(forged["spec"])  # authorization still old digest
        with self.assertRaisesRegex(q.QueueError, "authorization"):
            q.validate_document(forged)

    def test_malformed_queue_fails_closed_and_never_falls_back(self):
        store = TreeRef()
        observed = store.read()
        for raw in (b"not json", b"{}", json.dumps({**q.submit(TreeRef(), spec(),
                    expected_queue_revision=None, **AUTH), "revision": 0}).encode()):
            store.blobs[observed.tree] = {q.QUEUE_FILE: raw}
            with self.subTest(raw[:10]), self.assertRaises(q.QueueError):
                doc = q.load(store, observed)
                q.active_tasks(doc, legacy=TASKS, legacy_allowed=True)

    def test_legacy_registry_only_when_queue_absent_and_eligible(self):
        self.assertEqual(q.active_tasks(None, legacy=TASKS, legacy_allowed=True), TASKS)
        with self.assertRaisesRegex(q.QueueError, "legacy"):
            q.active_tasks(None, legacy=TASKS, legacy_allowed=False)

    def test_blocked_head_is_never_skipped(self):
        store = TreeRef()
        doc = q.submit(store, spec(issues=(1, 7)), expected_queue_revision=None, **AUTH)
        q.set_progress(store, 1, "BLOCKED", {"reason": "scope"}, expected_spec_digest=doc["spec_digest"])
        self.assertEqual(q.next_task(q.load(store, store.read())).issue, 1)


class GitHubRefStoreTreeTests(unittest.TestCase):
    def _store(self):
        from github_ref_lease import GitHubRefStore
        return GitHubRefStore("DaniilSydorenko/.github", "t")

    def test_tree_write_must_not_change_lease_state(self):
        store = self._store()
        observed = Snapshot("a" * 40, "b" * 40, initial_state())
        changed = {**initial_state(), "revision": 1, "phase": "RESERVED"}
        with patch.object(store, "_call") as call, self.assertRaises(LeaseError):
            store.advance(observed, changed, tree="c" * 40)
        call.assert_not_called()

    def test_lease_transition_reuses_observed_tree(self):
        store = self._store()
        observed = Snapshot("a" * 40, "b" * 40, initial_state())
        with patch.object(store, "_call", side_effect=[{"sha": "d" * 40}, {}]) as call:
            store.advance(observed, {**initial_state(), "revision": 1})
        self.assertEqual(call.call_args_list[0].args[2]["tree"], "b" * 40)

    def test_queue_write_commits_the_new_tree(self):
        store = self._store()
        observed = Snapshot("a" * 40, "b" * 40, initial_state())
        with patch.object(store, "_call", side_effect=[{"sha": "d" * 40}, {}]) as call:
            store.advance(observed, {**initial_state(), "revision": 1}, tree="c" * 40)
        self.assertEqual(call.call_args_list[0].args[2]["tree"], "c" * 40)
        self.assertEqual(call.call_args_list[1].args[2], {"sha": "d" * 40, "force": False})

    def test_read_file_absent_vs_invalid(self):
        import base64
        store = self._store()
        with patch.object(store, "_call", return_value={"tree": [], "truncated": False}):
            self.assertIsNone(store.read_file("b" * 40, q.QUEUE_FILE))
        with patch.object(store, "_call", return_value={"tree": [], "truncated": True}), \
                self.assertRaises(LeaseError):
            store.read_file("b" * 40, q.QUEUE_FILE)
        entry = {"path": q.QUEUE_FILE, "type": "blob", "sha": "e" * 40}
        with patch.object(store, "_call", side_effect=[{"tree": [entry]},
                          {"encoding": "base64", "content": base64.b64encode(b"{}").decode()}]):
            self.assertEqual(store.read_file("b" * 40, q.QUEUE_FILE), b"{}")


class AuthenticatedLeaseReadTests(unittest.TestCase):
    def test_lease_read_uses_gh_token_when_present(self):
        import io
        import cursor_protected_dispatch as d
        seen = []

        def fake(req, timeout):
            seen.append(req.headers.get("Authorization"))
            return io.BytesIO(b"{}")

        with patch("urllib.request.urlopen", fake), patch.dict("os.environ", {"GH_TOKEN": "tok"}):
            d._github_get(d.LEASE_REPO, "/git/ref/heads/x")
        with patch("urllib.request.urlopen", fake), patch.dict("os.environ", {}, clear=True):
            d._github_get(d.LEASE_REPO, "/git/ref/heads/x")
        self.assertEqual(seen, ["Bearer tok", None])
        with self.assertRaisesRegex(ValueError, "allowlisted"):
            d._github_get("someone/else", "")


if __name__ == "__main__":
    unittest.main()
