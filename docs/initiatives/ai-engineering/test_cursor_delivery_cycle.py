"""Offline regression for the managed Cursor delivery cycle (no network, no POST)."""
from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

import managed_cursor_launch
from cursor_acceptance import evaluate
from cursor_bundle_builder import build_launch_bundle
from cursor_delivery_cycle import advance, reject
from cursor_execution_observer import observe_once, observe_run, reconcile_dispatching
from cursor_pr_binding import discover_and_verify
from cursor_protected_dispatch import (
    APPROVED_OPERATION, OWNER_ATTESTATIONS, ProtectedCursorContext, request_id_for_dispatch,
    run_gates_only,
)
from cursor_readonly import CursorReadError
from cursor_tasks import DEFAULT_MODEL, TASKS, CursorTask, validate_registry
from github_ref_lease import Controller, fingerprint
from preview_one import preview_one
from sequential_handoff import preview_next_after_merge
from test_github_ref_lease import MemoryGitRef

TASK = TASKS[0]
REPO = TASK.repository
PATH = TASK.allowed_paths[0]
START, HEAD, HEAD2, MERGE = "1" * 40, "2" * 40, "3" * 40, "4" * 40
RID = request_id_for_dispatch(TASK)
AGENT = managed_cursor_launch.agent_id_for(RID)
RUN = "run-00000000-0000-0000-0000-0000000000aa"
PR = f"https://github.com/{REPO}/pull/301"
ISSUE_URL = TASK.issue_url
OWNER = "DaniilSydorenko"
ALL_ATTESTED = {k: True for k in OWNER_ATTESTATIONS}
CTX = ProtectedCursorContext("DaniilSydorenko/.github", OWNER, "refs/heads/main",
                             "workflow_dispatch", "1", APPROVED_OPERATION, TASK.issue, "9", False)


class FakeGH:
    """Path-keyed GitHub REST fake; params are ignored unless a callable is used."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get_json(self, path, params=None):
        self.calls.append((path, params))
        if path not in self.routes:
            raise AssertionError("unexpected GitHub path " + path)
        value = self.routes[path]
        return value(params) if callable(value) else copy.deepcopy(value)


class FakeCursor:
    """GET-only provider fake. Has no create/post method on purpose."""

    def __init__(self, *, run_status="FINISHED", agent_status="IDLE", branches=None,
                 agent_missing=False, fail_reads=0, models=(DEFAULT_MODEL,), agents=()):
        self.run_status, self.agent_status = run_status, agent_status
        self.branches = branches if branches is not None else [
            {"repoUrl": "github.com/" + REPO, "branch": "cursor/doc-220", "prUrl": PR}]
        self.agent_missing, self.fail_reads = agent_missing, fail_reads
        self.models, self.agents, self.calls = models, list(agents), []

    def get_json(self, path, params=None):
        self.calls.append(path)
        if self.fail_reads:
            self.fail_reads -= 1
            raise CursorReadError("Cursor HTTP 503 (body withheld)", status=503)
        if path == "/v1/me":
            return {"apiKeyName": "ci", "createdAt": "2026-01-01T00:00:00Z"}
        if path == "/v1/models":
            return {"items": [{"id": m} for m in self.models]}
        if path == "/v1/agents":
            return {"items": self.agents}
        if path == f"/v1/agents/{AGENT}":
            if self.agent_missing:
                raise CursorReadError("Cursor HTTP 404 (body withheld)", status=404)
            return {"id": AGENT, "status": self.agent_status, "latestRunId": RUN,
                    "repos": [{"url": "https://github.com/" + REPO, "startingRef": START}]}
        if path == f"/v1/agents/{AGENT}/runs/{RUN}":
            return {"id": RUN, "agentId": AGENT, "status": self.run_status,
                    "createdAt": "2026-11-26T10:00:00Z", "updatedAt": "2026-11-26T10:05:00Z",
                    "git": {"branches": self.branches}}
        raise AssertionError("unexpected Cursor path " + path)


def pr_body(*, state="open", merged=False, head=HEAD, base="master", head_ref="cursor/doc-220",
            fork=False, merged_by=None):
    return {"number": 301, "state": state, "merged": merged, "merge_commit_sha": MERGE,
            "merged_by": {"login": merged_by} if merged_by else None,
            "head": {"sha": head, "ref": head_ref,
                     "repo": {"full_name": "someone/fork" if fork else REPO}},
            "base": {"ref": base, "repo": {"full_name": REPO}}}


def check(name, conclusion="success", status="completed"):
    return {"name": name, "status": status, "conclusion": conclusion}


def gh_routes(*, pr=None, files=(PATH,), checks=None, reviews=None, open_prs=None,
              compare="ahead", head=HEAD, merge_compare=None):
    pr = pr if pr is not None else pr_body(head=head)
    checks = checks if checks is not None else [check(n) for n in TASK.required_checks]
    # Managed Cursor PRs are authored by the owner account, so by default there
    # is no owner approval at all (GitHub forbids self-approval).
    reviews = reviews if reviews is not None else []
    open_list = open_prs if open_prs is not None else (
        [{"number": 301, "head": {"ref": "cursor/doc-220"}}] if pr["state"] == "open" else [])
    return {
        f"/repos/{REPO}/pulls/301": pr,
        f"/repos/{REPO}/pulls/301/files": [{"filename": f} for f in files],
        f"/repos/{REPO}/pulls/301/reviews": reviews,
        f"/repos/{REPO}/commits/{pr['head']['sha']}/check-runs": {"check_runs": checks},
        f"/repos/{REPO}/compare/{START}...{pr['head']['sha']}": {"status": compare, "behind_by": 0},
        f"/repos/{REPO}/compare/{MERGE}...master": merge_compare or {"status": "ahead",
                                                                    "behind_by": 0},
        f"/repos/{REPO}/pulls": open_list,
    }


def lease_in(phase, *, pr_url=None, run_id=RUN, request_id=RID, source=ISSUE_URL):
    store = MemoryGitRef()
    gate = Controller(store)
    gate.acquire(request_id, source)
    if phase == "RESERVED":
        return store
    gate.transition(request_id, "RESERVED", "DISPATCHING")
    if phase == "DISPATCHING":
        return store
    gate.transition(request_id, "DISPATCHING", "RUNNING", run_id=run_id)
    if phase == "RUNNING":
        return store
    gate.transition(request_id, "RUNNING", "VERIFYING")
    if pr_url and pr_url != source:
        gate.bind_generated_pr(request_id, expected_issue_url=source, generated_pr_url=pr_url)
    if phase == "BLOCKED":
        gate.transition(request_id, "VERIFYING", "BLOCKED")
    return store


class RegistryTests(unittest.TestCase):
    def test_registry_is_valid_and_rejects_bad_entries(self):
        validate_registry()
        for bad in (CursorTask(REPO, 1, 1, ("../x",), ("CI",)),
                    CursorTask(REPO, 1, 1, ("a",), ()),
                    CursorTask(REPO, 1, 1, ("a",), ("CI",), scope="anything")):
            with self.assertRaises(ValueError):
                validate_registry((bad,))
        with self.assertRaises(ValueError):
            validate_registry((TASK, TASK))


class ObserverTests(unittest.TestCase):
    def test_terminal_states_are_mapped(self):
        for status, state in (("FINISHED", "SUCCEEDED"), ("ERROR", "FAILED"),
                              ("CANCELLED", "CANCELLED"), ("EXPIRED", "EXPIRED")):
            obs = observe_once(FakeCursor(run_status=status), AGENT, RUN, now=0)
            self.assertEqual(obs["state"], state)

    def test_active_then_stale(self):
        fresh = observe_once(FakeCursor(run_status="RUNNING"), AGENT, RUN,
                             now=1795600000.0 - 10**9)
        self.assertEqual(fresh["state"], "IN_PROGRESS")
        stale = observe_once(FakeCursor(run_status="WAITING_FOR_BACKGROUND_WORK"), AGENT, RUN,
                             now=4102444800.0)
        self.assertEqual(stale["state"], "STALE")

    def test_unknown_status_and_bad_identity(self):
        self.assertEqual(observe_once(FakeCursor(run_status="PAUSED"), AGENT, RUN, now=0)["state"],
                         "UNKNOWN")
        self.assertEqual(observe_once(FakeCursor(), "bc-bad", RUN, now=0)["state"], "UNKNOWN")

    def test_polling_is_bounded_and_survives_transient_errors(self):
        sleeps = []
        obs = observe_run(FakeCursor(run_status="RUNNING"), AGENT, RUN, max_polls=4,
                          interval_s=1, sleep=sleeps.append, clock=lambda: 0)
        self.assertEqual((obs["state"], obs["polls"], len(sleeps)), ("IN_PROGRESS", 4, 3))
        recovered = observe_run(FakeCursor(fail_reads=2), AGENT, RUN, max_polls=5,
                                interval_s=0, sleep=lambda _: None, clock=lambda: 0)
        self.assertEqual((recovered["state"], recovered["polls"]), ("SUCCEEDED", 3))
        with self.assertRaises(ValueError):
            observe_run(FakeCursor(), AGENT, RUN, max_polls=0)

    def test_reconcile_dispatching(self):
        self.assertEqual(reconcile_dispatching(FakeCursor(), AGENT)["state"], "RUN_FOUND")
        self.assertEqual(reconcile_dispatching(FakeCursor(agent_missing=True), AGENT)["state"],
                         "AGENT_ABSENT")
        self.assertEqual(reconcile_dispatching(FakeCursor(fail_reads=1), AGENT)["state"],
                         "UNAVAILABLE")


class BindingTests(unittest.TestCase):
    def bind(self, routes=None, branches=None, **kw):
        cursor = FakeCursor(branches=branches)
        return discover_and_verify(FakeGH(routes or gh_routes()), TASK,
                                   provider_branches=cursor.branches, starting_sha=START, **kw)

    def test_happy_path_binds_exact_pr(self):
        out = self.bind()
        self.assertEqual((out["decision"], out["pr_number"], out["head_sha"]), ("BIND", 301, HEAD))

    def test_failure_modes(self):
        cases = {
            "provider_reported_foreign_repository": dict(branches=[
                {"repoUrl": "github.com/evil/repo", "prUrl": "https://github.com/evil/repo/pull/1"}]),
            "multiple_candidate_prs": dict(branches=[
                {"repoUrl": "github.com/" + REPO, "prUrl": PR},
                {"repoUrl": "github.com/" + REPO, "prUrl": PR.replace("301", "302")}]),
            "pr_wrong_base": dict(routes=gh_routes(pr=pr_body(base="develop"))),
            "pr_from_fork_or_other_repository": dict(routes=gh_routes(pr=pr_body(fork=True))),
            "pr_head_not_a_cursor_branch": dict(routes=gh_routes(pr=pr_body(head_ref="feature/x"))),
            "pr_out_of_scope_changes": dict(routes=gh_routes(files=(PATH, "src/index.ts"))),
            "pr_head_not_descended_from_starting_sha": dict(routes=gh_routes(compare="diverged")),
            "competing_open_prs": dict(routes=gh_routes(open_prs=[{"number": 301}, {"number": 9}])),
            "pr_already_merged_before_acceptance": dict(routes=gh_routes(
                pr=pr_body(state="closed", merged=True))),
        }
        for reason, kw in cases.items():
            with self.subTest(reason):
                self.assertEqual(self.bind(**kw)["reason"], reason)

    def test_no_pr_and_closed_pr(self):
        self.assertEqual(self.bind(branches=[])["decision"], "NO_PR")
        closed = self.bind(routes=gh_routes(pr=pr_body(state="closed")))
        self.assertEqual(closed["decision"], "REJECTED")

    def test_branch_only_report_is_resolved_through_github(self):
        routes = gh_routes()
        routes[f"/repos/{REPO}/pulls"] = lambda params: (
            [{"number": 301}] if params.get("head") == "DaniilSydorenko:cursor/doc-220"
            else [{"number": 301, "head": {"ref": "cursor/doc-220"}}])
        out = self.bind(routes=routes,
                        branches=[{"repoUrl": "github.com/" + REPO, "branch": "cursor/doc-220"}])
        self.assertEqual(out["decision"], "BIND")


class AcceptanceTests(unittest.TestCase):
    def result(self, routes=None, bound=HEAD, **kw):
        return evaluate(FakeGH(routes or gh_routes(**kw)), TASK, pr_number=301,
                        bound_head_sha=bound)

    def status(self, **kw):
        return self.result(**kw)["status"]

    MERGED = dict(state="closed", merged=True, merged_by=OWNER)

    def test_owner_authored_pr_is_eligible_without_self_approval(self):
        out = self.result()  # no reviews at all: the owner authored the PR
        self.assertEqual((out["status"], out["reason"]),
                         ("INTEGRATION_ELIGIBLE", "ready_for_owner_review_and_merge"))
        self.assertIs(out["owner_approved_exact_head"], False)
        self.assertEqual((out["exact_head"], out["ci"]), (HEAD, "SUCCESS"))
        # An approval (possible for a non-owner-authored PR) is informational only.
        approved = self.result(reviews=[{"user": {"login": OWNER}, "state": "APPROVED",
                                         "commit_id": HEAD}])
        self.assertEqual(approved["status"], "INTEGRATION_ELIGIBLE")
        self.assertIs(approved["owner_approved_exact_head"], True)

    def test_eligible_is_never_integrated_and_needs_green_exact_head_ci(self):
        self.assertNotEqual(self.status(), "INTEGRATED")
        self.assertEqual(self.status(checks=[check("Test and build")]), "PENDING_CI")
        self.assertEqual(self.status(checks=[check("Test and build", None, "in_progress"),
                                             check("Gitleaks")]), "PENDING_CI")
        self.assertEqual(self.status(checks=[check("Test and build", "failure"),
                                             check("Gitleaks")]), "REJECTED")
        self.assertEqual(self.status(checks=[check(n) for n in TASK.required_checks]
                                     + [check("Benchmarks", "failure")]), "REJECTED")
        self.assertEqual(self.status(files=("src/x.ts",)), "REJECTED")
        self.assertEqual(self.status(pr=pr_body(state=None)), "STOP")

    def test_stale_head_is_never_accepted(self):
        for pr in (pr_body(head=HEAD2), pr_body(head=HEAD2, **self.MERGED)):
            with self.subTest(state=pr["state"]):
                out = self.result(routes=gh_routes(pr=pr), bound=HEAD)
                self.assertEqual((out["status"], out["reason"]),
                                 ("STOP", "pr_head_moved_after_binding"))

    def test_owner_merge_of_verified_head_is_integrated(self):
        out = self.result(pr=pr_body(**self.MERGED))  # still no approval review
        self.assertEqual((out["status"], out["merged_by"], out["merge_sha"]),
                         ("INTEGRATED", OWNER, MERGE))

    def test_unauthorized_or_unverified_merge_keeps_lease(self):
        cases = {
            "merged_by_non_owner": dict(pr=pr_body(state="closed", merged=True,
                                                   merged_by="cursor[bot]")),
            "merged_by_non_owner ": dict(pr=pr_body(state="closed", merged=True, merged_by=None)),
            "merged_without_green_exact_head_ci": dict(
                pr=pr_body(**self.MERGED), checks=[check("Test and build", "failure"),
                                                   check("Gitleaks")]),
            "merged_without_green_exact_head_ci ": dict(
                pr=pr_body(**self.MERGED), checks=[check("Gitleaks")]),
            "merge_commit_not_on_default_branch": dict(
                pr=pr_body(**self.MERGED), merge_compare={"status": "diverged", "behind_by": 3}),
            "merge_commit_not_on_default_branch ": dict(
                pr={**pr_body(**self.MERGED), "merge_commit_sha": None}),
        }
        for reason, kw in cases.items():
            with self.subTest(reason):
                out = self.result(**kw)
                self.assertEqual((out["status"], out["reason"]), ("STOP", reason.strip()))

    def test_missing_evidence_fails_closed(self):
        routes = gh_routes(pr=pr_body(**self.MERGED))
        routes[f"/repos/{REPO}/commits/{HEAD}/check-runs"] = {"message": "rate limited"}
        self.assertEqual(self.result(routes=routes)["reason"], "check_run_inventory_incomplete")
        routes = gh_routes(pr=pr_body(**self.MERGED))
        routes[f"/repos/{REPO}/pulls/301/files"] = {"message": "error"}
        self.assertEqual(self.result(routes=routes)["reason"], "pr_file_inventory_incomplete")
        routes = gh_routes()
        routes[f"/repos/{REPO}/pulls/301"] = None
        self.assertEqual(self.result(routes=routes)["reason"], "pr_unreadable")
        self.assertEqual(self.status(pr=pr_body(state="closed")), "REJECTED")


def collected(**facts):
    base = {"repo": REPO, "issue_number": TASK.issue, "issue_state": "open", "default_sha": START,
            "related_prs": [], "linked_pr_inventory_truncated": False,
            "issue_events_pagination_complete": True,
            "related_prs_files_pagination_complete": True}
    base.update(facts)
    return {"status": "OBSERVED", "missing_capabilities": [], "observed_facts": base}


def bundle_gh(open_prs=(), extra=None):
    routes = {f"/repos/{REPO}/pulls": list(open_prs),
              f"/repos/{REPO}/issues/{TASK.issue}": {"state": "open"}}
    routes.update(extra or {})
    return FakeGH(routes)


class BundleTests(unittest.TestCase):
    def build(self, gh=None, **kw):
        args = dict(collected=collected(), main_sha=START, lease_state={"phase": "IDLE"},
                    owner_bootstrap_authorized=True)
        args.update(kw)
        return build_launch_bundle(gh or bundle_gh(), TASK, **args)

    def test_bootstrap_bundle_passes_both_existing_contracts(self):
        b = self.build()
        self.assertEqual(preview_one(b["preview"])["decision"], "READY_FOR_OWNER_DISPATCH")
        h = preview_next_after_merge(b["handoff"])
        self.assertEqual((h["action"], h["proposed_request_id"]), ("READY_FOR_OWNER_DISPATCH", RID))
        self.assertEqual(b["handoff"]["previous"]["kind"], "BOOTSTRAP")

    def test_bootstrap_without_owner_authorization_stops_in_handoff(self):
        b = self.build(owner_bootstrap_authorized=False)
        self.assertEqual(preview_next_after_merge(b["handoff"])["reason"],
                         "bootstrap_not_authorized_or_unverified")

    def test_stops(self):
        self.assertEqual(self.build(gh=bundle_gh(open_prs=[{"number": 233}]))["reason"],
                         "target_repository_has_open_prs")
        self.assertEqual(self.build(main_sha=HEAD)["reason"], "default_sha_moved_between_reads")
        self.assertEqual(self.build(collected=collected(issue_state="closed"))["reason"],
                         "issue_not_open_or_identity_mismatch")
        self.assertEqual(self.build(lease_state={"phase": "VERIFYING"})["reason"], "lease_not_idle")
        self.assertEqual(self.build(previous_pr_number=301)["reason"],
                         "choose_bootstrap_or_previous_pr_not_both")
        partial = {"status": "PARTIAL", "missing_capabilities": ["complete_bounded_inventory"],
                   "observed_facts": {}}
        self.assertEqual(self.build(collected=partial)["reason"], "github_collection_incomplete")

    def related(self, *records, **facts):
        return self.build(collected=collected(related_prs=list(records), **facts))

    def test_closed_unmerged_related_pr_is_history_not_a_blocker(self):
        b = self.related({"number": 224, "state": "closed", "merged": False})
        self.assertEqual(preview_one(b["preview"])["decision"], "READY_FOR_OWNER_DISPATCH")
        self.assertEqual(preview_next_after_merge(b["handoff"])["action"],
                         "READY_FOR_OWNER_DISPATCH")

    def test_open_merged_or_unknown_related_prs_still_block(self):
        closed = {"number": 224, "state": "closed", "merged": False}
        cases = {
            "open": ({"number": 5, "state": "open", "merged": False}, [5]),
            "merged": ({"number": 6, "state": "closed", "merged": True}, [6]),
            "state_unknown": ({"number": 7, "state": None, "merged": False}, [7]),
            "merge_unknown": ({"number": 8, "state": "closed"}, [8]),
            "merge_not_bool": ({"number": 9, "state": "closed", "merged": "false"}, [9]),
            "bare_record": ({"number": 10}, [10]),
            "not_a_record": ("#11", [None]),
        }
        for name, (record, prs) in cases.items():
            with self.subTest(name):
                out = self.related(closed, record)
                self.assertEqual((out["reason"], out["detail"]["prs"]),
                                 ("related_prs_exist_review_first", prs))

    def test_incomplete_related_inventory_fails_closed(self):
        for facts in (dict(related_prs=None), dict(linked_pr_inventory_truncated=True),
                      dict(linked_pr_inventory_truncated=None),
                      dict(issue_events_pagination_complete=False),
                      dict(issue_events_pagination_complete=None),
                      dict(related_prs_files_pagination_complete=False)):
            with self.subTest(facts):
                self.assertEqual(self.build(collected=collected(**facts))["reason"],
                                 "related_pr_inventory_unverified")

    def previous_gh(self, **pr_kw):
        pr = pr_body(**{"state": "closed", "merged": True, "merged_by": OWNER, **pr_kw})
        # No reviews route: acceptance must not depend on an (impossible) self-approval.
        extra = {
            f"/repos/{REPO}/pulls/301": pr,
            f"/repos/{REPO}/compare/{MERGE}...master": {"status": "ahead"},
            f"/repos/{REPO}/commits/{HEAD}/check-runs": {"check_runs": [
                check(n) for n in TASK.required_checks]},
        }
        return bundle_gh(extra=extra)

    def test_previous_merge_is_verified_live(self):
        b = self.build(gh=self.previous_gh(), owner_bootstrap_authorized=False,
                       previous_pr_number=301)
        previous = b["handoff"]["previous"]
        self.assertEqual((previous["owner_merge_permission"], previous["owner_visual_acceptance"]),
                         ("granted", "accepted"))
        self.assertEqual(preview_next_after_merge(b["handoff"])["action"], "READY_FOR_OWNER_DISPATCH")
        for kw in (dict(merged_by="cursor[bot]"), dict(merged_by=None),
                   dict(merged=False, merged_by=OWNER)):
            with self.subTest(kw):
                other = self.build(gh=self.previous_gh(**kw), owner_bootstrap_authorized=False,
                                   previous_pr_number=301)
                self.assertEqual(other["handoff"]["previous"]["owner_visual_acceptance"], "pending")
                self.assertNotEqual(preview_next_after_merge(other["handoff"])["action"],
                                    "READY_FOR_OWNER_DISPATCH")


class FakeCreate:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def create(self, payload):
        self.calls.append(payload)
        if self.fail:
            raise managed_cursor_launch.LaunchUncertain("lost response")
        return {"agent_id": payload["agentId"], "run_id": RUN}


class DispatchTests(unittest.TestCase):
    def dispatch(self, store, create, cursor=None):
        def builder(*, task, main_sha, lease_state, inventory):
            return build_launch_bundle(bundle_gh(), task, collected=collected(), main_sha=main_sha,
                                       lease_state=lease_state, owner_bootstrap_authorized=True)
        with patch.object(managed_cursor_launch, "PILOT_ACTIVATION_ENABLED", True), \
                patch.object(managed_cursor_launch, "_trusted_lease_ref_audit", lambda c: True):
            return run_gates_only(
                CTX, issue_preflight=lambda: {
                    "reason": "scope_preflight_passed_but_live_gates_unverified"},
                lease_state_reader=lambda: store.read().state, main_sha_reader=lambda: START,
                cursor_api=cursor or FakeCursor(), attestations=ALL_ATTESTED,
                bundle_builder=builder, controller=Controller(store), cursor_create=create)

    def test_exactly_one_paid_launch_then_replay_and_lease_block_it(self):
        store, create = MemoryGitRef(), FakeCreate()
        first = self.dispatch(store, create)
        self.assertEqual(first["decision"], "STARTED", first)
        self.assertEqual(len(create.calls), 1)
        self.assertEqual(create.calls[0]["repos"][0]["startingRef"], START)
        self.assertEqual(store.state["phase"], "RUNNING")
        again = self.dispatch(store, create)
        self.assertEqual(again["reason"], "global_lease_not_idle")
        self.assertEqual(len(create.calls), 1)

    def test_ambiguous_create_keeps_lock_and_is_reconciled_without_post(self):
        store, create = MemoryGitRef(), FakeCreate(fail=True)
        out = self.dispatch(store, create)
        self.assertEqual(out["managed_launch_state"], "STOP_LOCK_HELD")
        self.assertTrue(out["cursor_post_attempted"])
        self.assertEqual(store.state["phase"], "DISPATCHING")
        step = advance(store=store, gh=None, cursor_api=FakeCursor(), ctx=CTX,
                       attestations=ALL_ATTESTED, dispatch=lambda s: self.fail("no dispatch"))
        self.assertEqual((step["outcome"], store.state["phase"]), ("RUNNING", "RUNNING"))
        self.assertEqual(len(create.calls), 1)

    def test_busy_provider_blocks_before_lease(self):
        store, create = MemoryGitRef(), FakeCreate()
        busy = FakeCursor(agents=[{"id": "bc-00000000-0000-0000-0000-000000000009",
                                   "status": "ACTIVE"}])
        self.assertEqual(self.dispatch(store, create, busy)["reason"], "cursor_agent_busy")
        self.assertEqual((store.state["phase"], create.calls), ("IDLE", []))


class LifecycleTests(unittest.TestCase):
    def step(self, store, gh=None, cursor=None):
        return advance(store=store, gh=gh, cursor_api=cursor or FakeCursor(), ctx=CTX,
                       attestations=ALL_ATTESTED, dispatch=lambda s: {"decision": "STOP"},
                       max_polls=2, interval_s=0, sleep=lambda _: None)

    def test_full_cycle_running_to_released(self):
        store = lease_in("RUNNING")
        self.assertEqual(self.step(store)["outcome"], "VERIFYING")
        ready = self.step(store, FakeGH(gh_routes()))  # owner-authored PR, no approval
        self.assertEqual(ready["outcome"], "INTEGRATION_READY", ready)
        self.assertEqual(store.state["pr_url"], PR)
        self.assertEqual(store.state["phase"], "VERIFYING")  # eligible is not accepted
        merged = gh_routes(pr=pr_body(state="closed", merged=True, merged_by=OWNER), open_prs=[])
        done = self.step(store, FakeGH(merged))
        self.assertEqual(done["outcome"], "RELEASED", done)
        self.assertEqual(store.state["phase"], "IDLE")
        self.assertIn(fingerprint(RID), store.state["consumed_request_hashes"])

    def test_non_owner_merge_never_releases_lease(self):
        store = lease_in("VERIFYING", pr_url=PR)
        bot = gh_routes(pr=pr_body(state="closed", merged=True, merged_by="cursor[bot]"),
                        open_prs=[])
        out = self.step(store, FakeGH(bot))
        self.assertEqual((out["outcome"], out["acceptance"]["reason"]),
                         ("HOLD", "merged_by_non_owner"))
        self.assertEqual(store.state["phase"], "VERIFYING")

    def test_uncertain_provider_keeps_lease(self):
        for cursor in (FakeCursor(run_status="RUNNING"), FakeCursor(run_status="PAUSED"),
                       FakeCursor(fail_reads=5)):
            store = lease_in("RUNNING")
            self.assertEqual(self.step(store, cursor=cursor)["outcome"], "HOLD")
            self.assertEqual(store.state["phase"], "RUNNING")

    def test_absent_agent_blocks_and_no_pr_requires_owner(self):
        store = lease_in("DISPATCHING")
        self.assertEqual(self.step(store, cursor=FakeCursor(agent_missing=True))["outcome"],
                         "BLOCKED")
        store = lease_in("VERIFYING")
        out = self.step(store, FakeGH({}), FakeCursor(branches=[]))
        self.assertEqual(out["reason"], "no_pr_produced")
        self.assertEqual(store.state["phase"], "VERIFYING")

    def test_pending_ci_holds_and_failed_ci_needs_owner(self):
        store = lease_in("VERIFYING", pr_url=PR)
        pending = self.step(store, FakeGH(gh_routes(checks=[check("Gitleaks")])))
        self.assertEqual((pending["outcome"], pending["acceptance"]["status"]), ("HOLD", "PENDING_CI"))
        failed = self.step(store, FakeGH(gh_routes(checks=[check("Test and build", "failure"),
                                                           check("Gitleaks")])))
        self.assertEqual(failed["outcome"], "OWNER_ACTION")
        self.assertEqual(store.state["phase"], "VERIFYING")

    def test_unregistered_legacy_lease_is_never_advanced(self):
        store = lease_in("VERIFYING", request_id="openhands-164-code-task-232",
                         source=f"https://github.com/{REPO}/issues/232", run_id="run-45690146434")
        self.assertEqual(self.step(store)["reason"], "lease_not_owned_by_registered_cursor_task")


class RejectTests(unittest.TestCase):
    def run_reject(self, store, gh, cursor=None, **kw):
        args = dict(request_id=RID, expected_lease_sha=store.read().sha, pr_url=PR,
                    owner_authorized=True)
        args.update(kw)
        return reject(store=store, gh=gh, cursor_api=cursor or FakeCursor(), **args)

    def closed_gh(self):
        return FakeGH(gh_routes(pr=pr_body(state="closed"), open_prs=[]))

    def test_closed_pr_release_is_idempotent_and_keeps_replay_protection(self):
        store = lease_in("VERIFYING", pr_url=PR)
        sha = store.read().sha
        self.assertEqual(self.run_reject(store, self.closed_gh())["outcome"], "REJECTED_RELEASED")
        self.assertEqual(store.state["phase"], "IDLE")
        again = self.run_reject(store, self.closed_gh(), expected_lease_sha=sha)
        self.assertEqual(again["outcome"], "ALREADY_RELEASED")
        self.assertEqual(Controller(store).acquire(RID, ISSUE_URL), "ALREADY_CONSUMED")

    def test_refusals(self):
        store = lease_in("VERIFYING", pr_url=PR)
        open_gh = FakeGH(gh_routes())
        cases = [
            ("owner_authorization_missing", dict(gh=self.closed_gh(), owner_authorized=False)),
            ("stale_lease_revision", dict(gh=self.closed_gh(), expected_lease_sha="f" * 40)),
            ("lease_identity_mismatch", dict(gh=self.closed_gh(), pr_url=PR.replace("301", "302"))),
            ("pr_not_closed_unmerged", dict(gh=open_gh)),
            ("provider_not_quiescent", dict(gh=self.closed_gh(),
                                            cursor=FakeCursor(run_status="RUNNING",
                                                              agent_status="ACTIVE"))),
            ("cursor_api_unavailable", dict(gh=self.closed_gh(), cursor=False)),
        ]
        for reason, kw in cases:
            with self.subTest(reason):
                gh = kw.pop("gh")
                cursor = kw.pop("cursor", None)
                out = reject(store=store, gh=gh,
                             cursor_api=None if cursor is False else (cursor or FakeCursor()),
                             request_id=RID, expected_lease_sha=kw.pop("expected_lease_sha",
                                                                       store.read().sha),
                             pr_url=kw.pop("pr_url", PR),
                             owner_authorized=kw.pop("owner_authorized", True))
                self.assertEqual(out["reason"], reason)
                self.assertEqual(store.state["phase"], "VERIFYING")

    def test_no_pr_rejection_and_legacy_actions_run(self):
        store = lease_in("BLOCKED")
        out = self.run_reject(store, FakeGH({f"/repos/{REPO}/pulls": []}), pr_url=ISSUE_URL)
        self.assertEqual(out["outcome"], "REJECTED_RELEASED")
        legacy_url = f"https://github.com/{REPO}/pull/233"
        legacy = lease_in("VERIFYING", request_id="openhands-164-code-task-232",
                          source=f"https://github.com/{REPO}/issues/232",
                          run_id="run-45690146434", pr_url=legacy_url)
        routes = {f"/repos/{REPO}/pulls/233": {"state": "closed", "merged": False},
                  "/repos/DaniilSydorenko/.github/actions/runs/45690146434": {"status": "in_progress"}}
        args = dict(request_id="openhands-164-code-task-232", pr_url=legacy_url)
        self.assertEqual(self.run_reject(legacy, FakeGH(routes), **args)["reason"],
                         "legacy_executor_run_not_completed")
        routes["/repos/DaniilSydorenko/.github/actions/runs/45690146434"] = {"status": "completed"}
        self.assertEqual(self.run_reject(legacy, FakeGH(routes), **args)["outcome"],
                         "REJECTED_RELEASED")

    def test_concurrent_lease_update_is_refused_not_retried(self):
        store = lease_in("VERIFYING", pr_url=PR)
        sha = store.read().sha
        gh = self.closed_gh()
        original = gh.get_json

        def racing(path, params=None):
            if path.endswith("/pulls/301"):
                store.sha = "e" * 40  # another writer advanced the ref meanwhile
            return original(path, params)

        gh.get_json = racing
        out = self.run_reject(store, gh, expected_lease_sha=sha)
        self.assertEqual(out["reason"], "lease_write_refused")
        self.assertEqual(store.state["phase"], "VERIFYING")


class CliTests(unittest.TestCase):
    OWNER_ENV = {"GITHUB_REPOSITORY": "DaniilSydorenko/.github", "GITHUB_ACTOR": OWNER,
                 "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
                 "GITHUB_RUN_ATTEMPT": "1", "GITHUB_RUN_ID": "5"}

    def test_cli_reject_requires_reject_operation_env(self):
        import cursor_delivery_cycle as cycle
        store = lease_in("VERIFYING", pr_url=PR)
        gh = FakeGH(gh_routes(pr=pr_body(state="closed"), open_prs=[]))
        argv = ["reject", "--request-id", RID, "--expected-lease-sha", store.read().sha,
                "--pr-url", PR]
        with patch.object(cycle, "_live", lambda: (store, gh, FakeCursor())), \
                patch.dict("os.environ", {**self.OWNER_ENV,
                                          "AI_ENG_APPROVED_OPERATION": "cursor-managed-delivery"},
                           clear=True):
            self.assertEqual(cycle.main(argv), 3)
        self.assertEqual(store.state["phase"], "VERIFYING")
        with patch.object(cycle, "_live", lambda: (store, gh, FakeCursor())), \
                patch.dict("os.environ", {**self.OWNER_ENV,
                                          "AI_ENG_APPROVED_OPERATION": "cursor-lease-reject"},
                           clear=True):
            self.assertEqual(cycle.main(argv), 0)
        self.assertEqual(store.state["phase"], "IDLE")

    def test_cli_advance_without_protected_context_stops(self):
        import cursor_delivery_cycle as cycle
        store = lease_in("RUNNING")
        with patch.object(cycle, "_live", lambda: (store, FakeGH({}), FakeCursor())), \
                patch.dict("os.environ", {}, clear=True):
            self.assertEqual(cycle.main(["advance"]), 3)
        self.assertEqual(store.state["phase"], "RUNNING")


class SequentialTests(unittest.TestCase):
    def test_next_registered_task_after_verified_previous_merge(self):
        import cursor_bundle_builder as builder
        second = CursorTask(REPO, 240, 2, ("src/distance.ts", "spec/distance.spec.ts"),
                            TASK.required_checks)
        queue = [TASK, second]
        pr = pr_body(state="closed", merged=True, merged_by=OWNER)
        routes = {
            f"/repos/{REPO}/pulls": [],
            f"/repos/{REPO}/issues/220": {"state": "closed", "state_reason": "completed"},
            f"/repos/{REPO}/issues/240": {"state": "open"},
            f"/repos/{REPO}/pulls/301": pr,
            f"/repos/{REPO}/compare/{MERGE}...master": {"status": "ahead"},
            f"/repos/{REPO}/commits/{HEAD}/check-runs": {"check_runs": [
                check(n) for n in TASK.required_checks]},
        }
        facts = collected(issue_number=240)
        with patch.object(builder, "queue_for", lambda repo: queue):
            b = build_launch_bundle(FakeGH(routes), second, collected=facts, main_sha=START,
                                    lease_state={"phase": "IDLE"}, previous_pr_number=301)
            h = preview_next_after_merge(b["handoff"])
            self.assertEqual((h["action"], h["next_issue_number"]), ("READY_FOR_OWNER_DISPATCH", 240))
            self.assertEqual(h["proposed_request_id"], request_id_for_dispatch(second))
            routes[f"/repos/{REPO}/issues/220"] = {"state": "closed", "state_reason": "not_planned"}
            b = build_launch_bundle(FakeGH(routes), second, collected=facts, main_sha=START,
                                    lease_state={"phase": "IDLE"}, previous_pr_number=301)
            self.assertEqual(preview_next_after_merge(b["handoff"])["reason"],
                             "closed_issue_not_accepted")


if __name__ == "__main__":
    unittest.main()
