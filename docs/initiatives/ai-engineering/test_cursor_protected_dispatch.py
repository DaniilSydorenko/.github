"""Offline regression for Haversine #220 protected Cursor dispatch gates."""
from __future__ import annotations

import io
import json
import urllib.error
from unittest import TestCase, main
from unittest.mock import patch

import cursor_protected_dispatch
from cursor_tasks import DEFAULT_MODEL

from cursor_protected_dispatch import (
    APPROVED_OPERATION,
    OWNER_ATTESTATIONS,
    attestations_from_env,
    request_id_for_dispatch,
    summarize_launch_attempt,
    ISSUE,
    ProtectedCursorContext,
    competing_writer_verdict,
    protected_context_from_env,
    live_lease_state,
    live_main_sha,
    run_gates_only,
)
from cursor_readonly import CursorReadError
from github_ref_lease import PREFIX, check_state, fingerprint
from managed_cursor_launch import PILOT_ACTIVATION_ENABLED


class CursorProtectedDispatchTests(TestCase):
    def setUp(self) -> None:
        self.ctx = ProtectedCursorContext(
            repository="DaniilSydorenko/.github",
            actor="DaniilSydorenko",
            ref="refs/heads/main",
            event_name="workflow_dispatch",
            run_attempt="1",
            operation=APPROVED_OPERATION,
            owner_go_issue=ISSUE,
            workflow_run_id="999",
            execute_cursor_requested=False,
        )
        self.idle = {
            "phase": "IDLE",
            "version": 1,
            "revision": 0,
            "request_id": None,
            "consumed_request_hashes": [],
        }
        self.preflight_ok = {
            "decision": "STOP",
            "reason": "scope_preflight_passed_but_live_gates_unverified",
        }
        self.main_sha = "f" * 40

    def test_pilot_activation_stays_off(self) -> None:
        self.assertIs(PILOT_ACTIVATION_ENABLED, False)

    def test_workflow_self_test_passes_with_activation_on(self) -> None:
        # ai-eng-cursor-delivery.yml runs --self-test before every live step;
        # flipping activation must not abort the run there (#206), and the
        # evidence-free fixture must still fail closed without a POST.
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True), \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            cursor_protected_dispatch.self_test()
        self.assertIn("activation ON (fail-closed)", out.getvalue())

    def test_workflow_self_test_passes_with_activation_off(self) -> None:
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            cursor_protected_dispatch.self_test()
        self.assertIn("activation OFF", out.getvalue())

    def test_env_context_requires_owner_operation(self) -> None:
        env = {
            "GITHUB_REPOSITORY": "DaniilSydorenko/.github",
            "GITHUB_ACTOR": "DaniilSydorenko",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_RUN_ID": "42",
            "AI_ENG_APPROVED_OPERATION": APPROVED_OPERATION,
            "AI_ENG_OWNER_GO_ISSUE": "220",
        }
        with patch.dict("os.environ", env, clear=True):
            ctx = protected_context_from_env()
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.owner_go_issue, 220)

    def test_gates_only_disabled_launch(self) -> None:
        result = run_gates_only(
            self.ctx,
            issue_preflight=lambda: self.preflight_ok,
            lease_state_reader=lambda: self.idle,
            main_sha_reader=lambda: self.main_sha,
        )
        self.assertEqual(result["decision"], "STOP")
        self.assertEqual(result["reason"], "owner_activation_not_enabled")
        self.assertFalse(result["live_cursor_dispatch_authorized"])
        self.assertNotEqual(result.get("competing_writer"), True)

    def test_competing_writer_blocks(self) -> None:
        rid = "cursor-test-request"
        busy = {
            **self.idle,
            "phase": "VERIFYING",
            "request_id": rid,
            "agent_id": "bc-00000000-0000-0000-0000-000000000000",
            "source_issue_url": (
                "https://github.com/DaniilSydorenko/haversine-geolocation/issues/232"
            ),
            "pr_url": "https://github.com/DaniilSydorenko/haversine-geolocation/pull/233",
            "run_id": "run-00000000-0000-0000-0000-000000000001",
            "revision": 3,
            "consumed_request_hashes": [fingerprint(rid)],
        }
        check_state(busy)
        writer = competing_writer_verdict(busy)
        self.assertTrue(writer["competing_writer"])
        result = run_gates_only(
            self.ctx,
            issue_preflight=lambda: self.preflight_ok,
            lease_state_reader=lambda: busy,
            main_sha_reader=lambda: self.main_sha,
        )
        self.assertEqual(result["reason"], "global_lease_not_idle")
        self.assertTrue(result["competing_writer"])

    def _fake_github(self, urls):
        class Body(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        lease = {"message": PREFIX + json.dumps(self.idle)}

        def fake(request, timeout=0):
            urls.append(request.full_url)
            if request.full_url.endswith("/haversine-geolocation"):
                return Body(json.dumps({"default_branch": "master"}).encode())
            if "/git/commits/" in request.full_url:
                return Body(json.dumps(lease).encode())
            return Body(json.dumps({"object": {"sha": "a" * 40}}).encode())

        return fake

    def test_target_master_sha_is_read_from_haversine_not_hq(self) -> None:
        urls: list[str] = []
        with patch("urllib.request.urlopen", self._fake_github(urls)):
            self.assertEqual(live_main_sha(), "a" * 40)
        self.assertEqual(urls, [
            "https://api.github.com/repos/DaniilSydorenko/haversine-geolocation",
            "https://api.github.com/repos/DaniilSydorenko/haversine-geolocation"
            "/git/ref/heads/master",
        ])

    def test_lease_is_read_from_hq(self) -> None:
        urls: list[str] = []
        with patch("urllib.request.urlopen", self._fake_github(urls)):
            self.assertEqual(live_lease_state()["phase"], "IDLE")
        self.assertTrue(all(u.startswith(
            "https://api.github.com/repos/DaniilSydorenko/.github/git/") for u in urls))

    def test_github_outage_fails_closed_instead_of_crashing(self) -> None:
        def down():
            raise urllib.error.URLError("unreachable")

        for field in ("lease_state_reader", "issue_preflight", "main_sha_reader"):
            readers = {
                "issue_preflight": lambda: self.preflight_ok,
                "lease_state_reader": lambda: self.idle,
                "main_sha_reader": lambda: self.main_sha,
                field: down,
            }
            result = run_gates_only(self.ctx, **readers)
            self.assertEqual(result["decision"], "STOP", field)
            self.assertFalse(result["cursor_post_attempted"], field)

    def test_gates_path_goes_through_real_managed_launch(self) -> None:
        calls = []
        real = cursor_protected_dispatch.launch_single_approved_issue

        def spy(**kwargs):
            calls.append(kwargs)
            return real(**kwargs)

        with patch.object(cursor_protected_dispatch, "launch_single_approved_issue", spy):
            result = run_gates_only(
                self.ctx,
                issue_preflight=lambda: self.preflight_ok,
                lease_state_reader=lambda: self.idle,
                main_sha_reader=lambda: self.main_sha,
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["managed_launch_state"], "DISABLED")
        self.assertEqual(result["reason"], "owner_activation_not_enabled")

    def test_activation_without_trusted_permit_still_stops(self) -> None:
        with patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            result = run_gates_only(
                self.ctx,
                issue_preflight=lambda: self.preflight_ok,
                lease_state_reader=lambda: self.idle,
                main_sha_reader=lambda: self.main_sha,
            )
        self.assertEqual(result["decision"], "STOP")
        self.assertFalse(result["cursor_post_attempted"])
        self.assertEqual(result["managed_launch_state"], "STOP")


    ALL_ATTESTED = {key: True for key in OWNER_ATTESTATIONS}

    class FakeCursor:
        def __init__(self, models=(DEFAULT_MODEL,), agents=()):
            self.models, self.agents, self.calls = models, list(agents), []

        def get_json(self, path, params=None):
            self.calls.append(path)
            if path == "/v1/me":
                return {"apiKeyName": "ci", "createdAt": "2026-01-01T00:00:00Z"}
            if path == "/v1/models":
                return {"items": [{"id": m, "displayName": m} for m in self.models]}
            if path == "/v1/agents":
                return {"items": self.agents}
            raise AssertionError("unexpected Cursor path " + path)

    def _run(self, **kwargs):
        args = dict(
            issue_preflight=lambda: self.preflight_ok,
            lease_state_reader=lambda: self.idle,
            main_sha_reader=lambda: self.main_sha,
        )
        args.update(kwargs)
        return run_gates_only(self.ctx, **args)

    def _spy_launch(self):
        calls = []
        real = cursor_protected_dispatch.launch_single_approved_issue

        def spy(**kwargs):
            calls.append(kwargs)
            return real(**kwargs)

        return calls, patch.object(cursor_protected_dispatch, "launch_single_approved_issue", spy)

    def test_request_id_is_deterministic_per_issue_not_per_run(self) -> None:
        rid = request_id_for_dispatch()
        self.assertEqual(rid, "seq-b71fef904d1a0cbe1eac77c552ea3f75")
        other = ProtectedCursorContext(**{**self.ctx.__dict__, "workflow_run_id": "1000"})
        self.assertEqual(run_gates_only(
            other, issue_preflight=lambda: self.preflight_ok,
            lease_state_reader=lambda: self.idle,
            main_sha_reader=lambda: self.main_sha)["request_id"], rid)

    def test_consumed_request_cannot_dispatch_again(self) -> None:
        consumed = {**self.idle, "consumed_request_hashes": [fingerprint(request_id_for_dispatch())]}
        result = self._run(lease_state_reader=lambda: consumed)
        self.assertEqual(result["reason"], "request_already_consumed")
        self.assertFalse(result["cursor_post_attempted"])

    def test_no_cursor_key_means_missing_evidence_and_empty_permit(self) -> None:
        calls, spy = self._spy_launch()
        with spy:
            result = self._run(attestations=self.ALL_ATTESTED)
        for item in ("cursor_inventory_clear", "verified_account_scope",
                     "verified_model_allowlist"):
            self.assertIn(item, result["permit_missing_evidence"])
        self.assertEqual(calls[0]["permit"], {})

    def test_missing_attestation_is_reported_not_assumed(self) -> None:
        partial = {**self.ALL_ATTESTED, "verified_cursor_billing": False}
        result = self._run(cursor_api=self.FakeCursor(), attestations=partial)
        self.assertEqual(result["permit_missing_evidence"], ["verified_cursor_billing"])

    def test_model_must_exist_in_live_cursor_model_list(self) -> None:
        result = self._run(cursor_api=self.FakeCursor(models=("composer-2",)),
                           attestations=self.ALL_ATTESTED)
        self.assertEqual(result["permit_missing_evidence"], ["verified_model_allowlist"])

    def test_provider_evidence_distinguishes_rejected_key_from_absent_model(self) -> None:
        absent = self._run(cursor_api=self.FakeCursor(models=("composer-2",)),
                           attestations=self.ALL_ATTESTED)["cursor_provider_evidence"]
        self.assertEqual(absent, {"api_configured": True, "key_info_ok": True,
                                  "pinned_model": DEFAULT_MODEL,
                                  "live_model_ids": ["composer-2"]})

        class Rejected:
            def get_json(self, path, params=None):
                raise CursorReadError("Cursor HTTP 401 (body withheld)", status=401)

        rejected = self._run(cursor_api=Rejected(),
                             attestations=self.ALL_ATTESTED)["cursor_provider_evidence"]
        self.assertEqual(rejected, {"api_configured": True, "key_info_ok": False,
                                    "pinned_model": DEFAULT_MODEL, "live_model_ids": []})
        unset = self._run(attestations=self.ALL_ATTESTED)["cursor_provider_evidence"]
        self.assertFalse(unset["api_configured"])

    def test_active_cursor_agent_blocks(self) -> None:
        busy = [{"id": "bc-00000000-0000-0000-0000-000000000009", "status": "ACTIVE"}]
        result = self._run(cursor_api=self.FakeCursor(agents=busy),
                           attestations=self.ALL_ATTESTED)
        self.assertEqual(result["reason"], "cursor_agent_busy")
        self.assertFalse(result["cursor_post_attempted"])

    def test_complete_evidence_builds_permit_and_stops_only_at_bundle(self) -> None:
        fake = self.FakeCursor()
        calls, spy = self._spy_launch()
        with spy, patch("managed_cursor_launch.PILOT_ACTIVATION_ENABLED", True):
            result = self._run(cursor_api=fake, attestations=self.ALL_ATTESTED)
        self.assertEqual(result["permit_missing_evidence"], [])
        permit = calls[0]["permit"]
        self.assertTrue(all(v is True for k, v in permit.items() if k.startswith("verified_")))
        self.assertEqual(permit["request_id"], request_id_for_dispatch())
        self.assertEqual(permit["head_sha"], self.main_sha)
        # Remaining gate: the live preview+handoff bundle is not built yet.
        self.assertEqual(result["managed_launch_reason"], "next_issue_preview_or_handoff_unverified")
        self.assertFalse(result["cursor_post_attempted"])
        self.assertNotIn("/v1/agents/bc-", " ".join(fake.calls))

    def test_attestations_require_exact_true(self) -> None:
        env = {var: "true" for var in OWNER_ATTESTATIONS.values()}
        self.assertTrue(all(attestations_from_env(env).values()))
        for value in ("True", "1", "yes", ""):
            self.assertFalse(any(attestations_from_env(
                {var: value for var in OWNER_ATTESTATIONS.values()}).values()))

    def test_held_lock_reports_possible_post(self) -> None:
        out = summarize_launch_attempt(
            {"state": "STOP_LOCK_HELD", "reason": "cursor_create_result_unknown"}, proposal=None)
        self.assertEqual(out["decision"], "STOP")
        self.assertTrue(out["cursor_post_attempted"])

    def test_no_writers_constructed_while_activation_off(self) -> None:
        env = {"AI_ENG_LEASE_WRITER_TOKEN": "t", "CURSOR_API_KEY": "k"}
        with patch.dict("os.environ", env):
            self.assertEqual(cursor_protected_dispatch._live_writers(), (None, None))



class SubagentResidualRiskTests(TestCase):
    """Pilot-only accepted risk (#205): waives, never verifies, the subagent gate for #220 only."""

    def setUp(self) -> None:
        import dataclasses
        from cursor_protected_dispatch import SUBAGENT_RISK, TASK_220, build_trusted_permit
        self.risk, self.build, self.task = SUBAGENT_RISK, build_trusted_permit, TASK_220
        self.other_task = dataclasses.replace(TASK_220, issue=221, order=2)
        CursorProtectedDispatchTests.setUp(self)  # reuse self.ctx fixture
        self.base = {k: True for k in OWNER_ATTESTATIONS}
        self.base["verified_subagents_disabled"] = False

    def _permit(self, attestations, task=None):
        return self.build(
            self.ctx, request_id="seq-x", main_sha="f" * 40, scope_preflight_passed=True,
            attestations=attestations, key_info_ok=True,
            live_models=frozenset({self.task.model}), inventory={"status": "CLEAR"},
            task=task or self.task)

    def test_accepted_risk_waives_gate_for_task_220_but_never_marks_verified(self) -> None:
        permit, missing = self._permit(self.base)
        self.assertEqual(missing, [])
        self.assertIs(permit["verified_subagents_disabled"], False)
        self.assertEqual(permit["accepted_residual_risks"], (self.risk,))

    def test_acceptance_does_not_extend_to_any_other_task(self) -> None:
        permit, missing = self._permit(self.base, task=self.other_task)
        self.assertEqual(missing, ["verified_subagents_disabled"])
        self.assertEqual(permit["accepted_residual_risks"], ())

    def test_without_acceptance_gate_stays_missing(self) -> None:
        permit, missing = self._permit({**self.base, "subagent_risk_accepted_task_220": False})
        self.assertEqual(missing, ["verified_subagents_disabled"])
        self.assertEqual(permit["accepted_residual_risks"], ())

    def test_real_attestation_records_no_residual_risk(self) -> None:
        permit, missing = self._permit({k: True for k in OWNER_ATTESTATIONS})
        self.assertEqual(missing, [])
        self.assertEqual(permit["accepted_residual_risks"], ())

    def test_acceptance_needs_exact_true_env(self) -> None:
        for value in ("True", "1", "yes", ""):
            env = {"AI_ENG_ACCEPT_SUBAGENT_RISK_TASK_220": value}
            self.assertIs(attestations_from_env(env)["subagent_risk_accepted_task_220"], False)
        self.assertIs(attestations_from_env(
            {"AI_ENG_ACCEPT_SUBAGENT_RISK_TASK_220": "true"})["subagent_risk_accepted_task_220"], True)

    def test_launch_gate_accepts_risk_only_for_bound_task_and_only_subagents(self) -> None:
        from managed_cursor_launch import _gate_ok
        ok = {"accepted_residual_risks": (self.risk,), "verified_subagents_disabled": False,
              "repository": self.task.repository, "issue_number": 220}
        self.assertTrue(_gate_ok(ok, "verified_subagents_disabled"))
        self.assertFalse(_gate_ok({**ok, "issue_number": 221}, "verified_subagents_disabled"))
        self.assertFalse(_gate_ok({**ok, "repository": "x/y"}, "verified_subagents_disabled"))
        self.assertFalse(_gate_ok({**ok, "accepted_residual_risks": [self.risk]},
                                  "verified_subagents_disabled"))
        self.assertFalse(_gate_ok({**ok, "accepted_residual_risks": ()},
                                  "verified_subagents_disabled"))
        for other in ("verified_cursor_billing", "verified_external_billing_excluded",
                      "verified_launch_route_exclusivity", "verified_account_scope",
                      "verified_model_allowlist", "verified_owner_security_gates"):
            self.assertFalse(_gate_ok(ok, other), other)

    def test_launch_gate_and_permit_agree_on_risk_id_and_target(self) -> None:
        from managed_cursor_launch import ACCEPTABLE_RISKS
        self.assertEqual(ACCEPTABLE_RISKS, {"verified_subagents_disabled": (
            self.risk, self.task.repository, self.task.issue)})

    def test_privileged_workflow_injects_every_owner_variable_readonly_none(self) -> None:
        from pathlib import Path
        wf = Path(__file__).resolve().parents[3] / ".github" / "workflows"
        delivery = (wf / "ai-eng-cursor-delivery.yml").read_text()
        probe = (wf / "ai-eng-cursor-api-probe.yml").read_text()
        for var in OWNER_ATTESTATIONS.values():
            self.assertIn(f"{var}: ${{{{ vars.{var} }}}}", delivery, var)
            self.assertNotIn(var, probe, var)

if __name__ == "__main__":
    main()