"""Offline adversarial tests for #164 protected live wiring (no network/model/writes)."""
from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest

from github_ref_lease import Controller
from openhands_164_live_wiring import (
    APPROVED_OPERATION,
    CONTROL_ACTOR,
    CONTROL_REPO,
    LiveExecutionConfig,
    LiveWiringRequest,
    ProtectedWorkflowContext,
    TERMINAL_PUBLISHED,
    TERMINAL_WIRED,
    evaluate_ci_evidence,
    protected_context_from_env,
    run_protected_live_wiring,
    verify_protected_context,
)
from openhands_164_executor import _TRUSTED_AUTHORIZATION
from openhands_164_patch_contract import ALLOWED
from openhands_164_sequential_handoff import IssueProof
from openhands_164_vertical_integration import CiEvidence
from openhands_runner_admission_bridge import ProviderBudgetAttestation, TrustedWorkflowAttestation
from openhands_live_orchestrator import EXPECTED
from openhands_lease_admission_adapter import request_id_for
from test_github_ref_lease import MemoryGitRef
from test_openhands_164_vertical_integration import trusted_attestation_from_store
from test_openhands_runner_admission_bridge import BUDGET_OK, trusted_bundle


def _repo(tmp: pathlib.Path) -> tuple[pathlib.Path, str]:
    root = tmp / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=Test", "-c",
         "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "base"],
        check=True,
    )
    sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    return root, sha


def _inventory(sha: str) -> dict:
    return {
        "reason": "live_authorization_not_integrated",
        "default_head": sha,
        "issues": [{"number": n, "target": p} for n, p in EXPECTED],
    }


def _write(ws: pathlib.Path, issue: int) -> None:
    path = ws / ALLOWED[issue]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("scoped pilot documentation\n", encoding="utf-8")


_UNSET = object()


def _good_ctx(issue: int = 216) -> ProtectedWorkflowContext:
    return ProtectedWorkflowContext(
        CONTROL_REPO, CONTROL_ACTOR, "refs/heads/main", "workflow_dispatch", "1",
        APPROVED_OPERATION, issue,
    )


class LiveWiringTests(unittest.TestCase):
    def _run(
        self,
        *,
        issue: int = 216,
        store: MemoryGitRef | None = None,
        trusted: TrustedWorkflowAttestation | None = None,
        budget: ProviderBudgetAttestation | None = None,
        protected: ProtectedWorkflowContext | None | object = _UNSET,
        prior_proofs=(),
        open_prs=(),
        ci: CiEvidence | None = None,
        base_sha: str | None = None,
        apply=None,
        live_mode: bool = False,
        wiring_mode: str | None = None,
        extra_config: LiveExecutionConfig | None = None,
        executor=None,
        publisher=None,
        publisher_transport=None,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root, sha = _repo(pathlib.Path(tmp))
            lease_store = store if store is not None else MemoryGitRef()
            if trusted is None:
                trusted = trusted_bundle(lease_store, issue=issue)
            if budget is None:
                budget = BUDGET_OK
            if protected is _UNSET:
                protected = _good_ctx(issue)
            req = LiveWiringRequest(
                issue, "555", _inventory(sha), trusted=trusted, budget=budget,
                protected=protected, prior_proofs=prior_proofs,
                open_prs_for_target=open_prs, ci_after_publish=ci,
            )
            mode = wiring_mode or ("live_execute" if live_mode else "offline_replay")
            return run_protected_live_wiring(
                req,
                lease_store=lease_store,
                workspace=root,
                base_sha=base_sha or sha,
                apply_agent_change=apply or (_write if not live_mode else None),
                wiring_mode=mode,
                live_config=extra_config,
                executor=executor,
                publisher=publisher,
                publisher_transport=publisher_transport,
            )

    def test_issue216_wiring_terminal_stop(self):
        out = self._run()
        self.assertEqual(out["reason"], TERMINAL_WIRED)
        self.assertTrue(out["patch_scope_verified"])
        self.assertFalse(out["model_invoked"])
        self.assertFalse(out["github_write"])

    def test_protected_context_missing(self):
        out = self._run(protected=None)
        self.assertEqual(out["reason"], "protected_workflow_context_missing")

    def test_owner_go_mismatch(self):
        out = self._run(protected=_good_ctx(217))
        self.assertEqual(out["reason"], "owner_go_issue_mismatch")

    def test_stale_base_sha(self):
        out = self._run(base_sha="b" * 40)
        self.assertEqual(out["reason"], "base_sha_mismatch")

    def test_duplicate_pr_collision(self):
        out = self._run(open_prs=[999])
        self.assertEqual(out["reason"], "duplicate_or_overlapping_pr")

    def test_sequential_gate_blocks_217(self):
        out = self._run(issue=217)
        self.assertEqual(out["reason"], "sequential_issue_not_eligible")

    def test_budget_denied(self):
        budget = type(BUDGET_OK)(verified_within_shared_cap=False, attestation_source="trusted_workflow_budget_probe")
        out = self._run(budget=budget)
        self.assertEqual(out["reason"], "provider_budget_not_verified")

    def test_ci_unknown_fails(self):
        self.assertEqual(evaluate_ci_evidence(CiEvidence("UNKNOWN", "SUCCESS"))["reason"], "ci_aggregate_incomplete")
        self.assertEqual(evaluate_ci_evidence(CiEvidence("SUCCESS", "PENDING"))["reason"], "ci_security_incomplete")
        self.assertEqual(evaluate_ci_evidence(CiEvidence("SUCCESS", "SUCCESS")), None)

    def test_protected_context_env_gate(self):
        ctx = _good_ctx()
        self.assertIsNone(verify_protected_context(ctx, 216))
        bad = ProtectedWorkflowContext(
            "other/repo", CONTROL_ACTOR, "refs/heads/main", "workflow_dispatch", "1", APPROVED_OPERATION, 216
        )
        self.assertEqual(verify_protected_context(bad, 216)["reason"], "wrong_control_repository")
        self.assertIsNone(protected_context_from_env())

    def test_lease_contention(self):
        store = MemoryGitRef()
        Controller(store).acquire(
            request_id_for(216),
            "https://github.com/DaniilSydorenko/haversine-geolocation/issues/216",
        )
        proof = IssueProof(
            216, ALLOWED[216],
            "https://github.com/DaniilSydorenko/haversine-geolocation/pull/500",
            "a" * 40, True, True, True, True,
        )
        out = self._run(
            issue=217, store=store, prior_proofs=(proof,),
            trusted=trusted_attestation_from_store(store, 217),
        )
        self.assertEqual(out["reason"], "lease_contention")

    def test_live_execute_mocked_executor_publisher(self):
        calls = {"model": 0, "publish": 0}

        def fake_executor(root, key, model, issue, *, authorization):
            calls["model"] += 1
            assert authorization is _TRUSTED_AUTHORIZATION
            _write(root, issue)

        def fake_publish(**kwargs):
            calls["publish"] += 1
            return {"html_url": "https://github.com/DaniilSydorenko/haversine-geolocation/pull/901"}

        out = self._run(
            live_mode=True,
            executor=fake_executor,
            publisher=fake_publish,
            publisher_transport=lambda *a, **k: {},
            extra_config=LiveExecutionConfig(
                live_attested=True,
                api_key="sk-or-test",
                publisher_token="ghp_test",
            ),
        )
        self.assertEqual(out["reason"], TERMINAL_PUBLISHED)
        self.assertTrue(out["model_invoked"])
        self.assertTrue(out["github_write"])
        self.assertEqual(calls["model"], 1)
        self.assertEqual(calls["publish"], 1)

    def test_live_not_attested_stops_before_model(self):
        out = self._run(live_mode=True, extra_config=LiveExecutionConfig(live_attested=False))
        self.assertEqual(out["reason"], TERMINAL_WIRED)
        self.assertFalse(out["model_invoked"])

    def test_already_satisfied_skips_model(self):
        satisfied = """# Runtime Compatibility
Node 22 Supported Node 24 Supported Node 26 smoke
minimum supported Node.js version
"""
        with tempfile.TemporaryDirectory() as tmp:
            root, sha = _repo(pathlib.Path(tmp))
            doc = root / ALLOWED[216]
            doc.parent.mkdir(parents=True, exist_ok=True)
            doc.write_text(satisfied, encoding="utf-8")
            store = MemoryGitRef()
            out = run_protected_live_wiring(
                LiveWiringRequest(
                    216, "556", _inventory(sha),
                    trusted=trusted_bundle(store),
                    budget=BUDGET_OK,
                    protected=_good_ctx(216),
                ),
                lease_store=store,
                workspace=root,
                base_sha=sha,
                wiring_mode="live_gates_only",
                live_config=LiveExecutionConfig(live_attested=True, api_key="x", publisher_token="y"),
            )
        self.assertEqual(out["reason"], "ALREADY_SATISFIED")
        self.assertFalse(out["model_invoked"])


if __name__ == "__main__":
    unittest.main()