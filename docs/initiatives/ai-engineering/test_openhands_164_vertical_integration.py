"""Offline adversarial tests for #164 vertical integration (no network/model/writes)."""
from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest

from github_ref_lease import Controller
from openhands_164_patch_contract import ALLOWED
from openhands_164_sequential_handoff import IssueProof
from openhands_164_vertical_integration import (
    CiEvidence,
    TERMINAL_OFFLINE,
    VerticalRequest,
    publisher_precheck,
    run_offline_vertical,
)
from openhands_lease_admission_adapter import (
    LeaseRefEvidence,
    RulesetEvidence,
    TargetHeadEvidence,
    WriterIdentityEvidence,
)
from github_ref_lease import agent_id_for
from test_lease_ruleset_candidate import APP_ID, GUARD, UPDATE
from openhands_runner_admission_bridge import TrustedWorkflowAttestation
from openhands_live_orchestrator import EXPECTED
from openhands_runner_admission_bridge import ProviderBudgetAttestation, evaluate_before_model_handoff
from test_github_ref_lease import MemoryGitRef
from test_openhands_runner_admission_bridge import BUDGET_OK, trusted_bundle
from openhands_lease_admission_adapter import request_id_for


def _git_repo(tmp: pathlib.Path) -> tuple[pathlib.Path, str]:
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


def _write_allowed(ws: pathlib.Path, issue: int) -> None:
    target = ws / ALLOWED[issue]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("pilot documentation change\n", encoding="utf-8")


def trusted_attestation_from_store(store, issue: int) -> TrustedWorkflowAttestation:
    rid = request_id_for(issue)
    snap = store.read()
    writer = agent_id_for(rid)
    head = snap.sha
    return TrustedWorkflowAttestation(
        expected_lease_sha=head,
        lease=LeaseRefEvidence(
            observed_ref_head_sha=head,
            snapshot_commit_sha=head,
            state=snap.state,
            authenticated_ref=True,
            exclusive_writer_verified=True,
            credential_path_verified=True,
        ),
        target_head=TargetHeadEvidence(head, head, head, True),
        writer=WriterIdentityEvidence(writer, True),
        ruleset=RulesetEvidence("ai-eng-cursor-lease-v1", [UPDATE, GUARD], APP_ID, True),
    )


def _good_proof(index: int) -> IssueProof:
    n, path = EXPECTED[index]
    return IssueProof(
        n, path,
        f"https://github.com/DaniilSydorenko/haversine-geolocation/pull/{500 + index}",
        "a" * 40, True, True, True, True,
    )


class VerticalIntegrationHappyPath(unittest.TestCase):
    def test_issue216_full_offline_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, sha = _git_repo(pathlib.Path(tmp))
            store = MemoryGitRef()
            req = VerticalRequest(
                216, "123456", _inventory(sha),
                trusted=trusted_bundle(store), budget=BUDGET_OK,
            )
            out = run_offline_vertical(
                req, lease_store=store, workspace=root, base_sha=sha, apply_agent_change=_write_allowed,
            )
            self.assertEqual(out["reason"], TERMINAL_OFFLINE)
            self.assertTrue(out["patch_scope_verified"])
            self.assertTrue(out["publisher_handoff_ready"])
            self.assertFalse(out["model_invoked"])
            self.assertFalse(out["github_write"])

    def test_issue217_requires_prior_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, sha = _git_repo(pathlib.Path(tmp))
            store = MemoryGitRef()
            req = VerticalRequest(
                217, "123457", _inventory(sha),
                trusted=trusted_bundle(store, issue=217), budget=BUDGET_OK,
                prior_proofs=(_good_proof(0),),
            )
            out = run_offline_vertical(
                req, lease_store=store, workspace=root, base_sha=sha, apply_agent_change=_write_allowed,
            )
            self.assertEqual(out["reason"], TERMINAL_OFFLINE)
            self.assertEqual(out["issue"], 217)


class VerticalIntegrationNegativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root, self.sha = _git_repo(pathlib.Path(self.tmp.name))
        self.inventory = _inventory(self.sha)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, issue: int, **kwargs):
        store = kwargs.pop("store", MemoryGitRef())
        default_trusted = trusted_bundle(store, issue=issue) if "trusted" not in kwargs else None
        req = VerticalRequest(
            issue, "654321", self.inventory,
            trusted=kwargs.pop("trusted", default_trusted),
            budget=kwargs.pop("budget", BUDGET_OK),
            prior_proofs=kwargs.pop("prior_proofs", ()),
            open_prs_for_target=kwargs.pop("open_prs", ()),
            ci_after_publish=kwargs.pop("ci", None),
        )
        return run_offline_vertical(
            req,
            lease_store=store,
            workspace=self.root,
            base_sha=kwargs.pop("base_sha", self.sha),
            apply_agent_change=kwargs.pop("apply", _write_allowed),
        )

    def test_stale_base_sha(self):
        out = self._run(216, base_sha="b" * 40)
        self.assertEqual(out["reason"], "base_sha_mismatch")

    def test_wrong_issue_path_change(self):
        def bad(ws: pathlib.Path, issue: int) -> None:
            (ws / ALLOWED[217]).parent.mkdir(parents=True, exist_ok=True)
            (ws / ALLOWED[217]).write_text("wrong\n", encoding="utf-8")

        out = self._run(216, apply=bad)
        self.assertEqual(out["reason"], "patch_scope_unverified")

    def test_duplicate_pr_collision(self):
        out = self._run(216, open_prs=[42])
        self.assertEqual(out["reason"], "duplicate_or_overlapping_pr")

    def test_budget_unknown(self):
        store = MemoryGitRef()
        out = self._run(
            216,
            store=store,
            budget=None,
        )
        self.assertEqual(out["reason"], "missing_provider_budget_attestation")

    def test_budget_exhausted(self):
        store = MemoryGitRef()
        budget = ProviderBudgetAttestation(False, "trusted_workflow_budget_probe")
        out = self._run(216, store=store, budget=budget)
        self.assertEqual(out["reason"], "provider_budget_not_verified")

    def test_missing_trusted_attestation(self):
        store = MemoryGitRef()
        out = self._run(216, store=store, trusted=None)
        self.assertEqual(out["reason"], "missing_trusted_workflow_attestation")

    def test_sequential_skip_denied(self):
        out = self._run(217)
        self.assertEqual(out["reason"], "sequential_issue_not_eligible")

    def test_no_executor_stops_at_admission(self):
        store = MemoryGitRef()
        req = VerticalRequest(216, "999001", self.inventory, trusted=trusted_bundle(store), budget=BUDGET_OK)
        out = run_offline_vertical(req, lease_store=store, workspace=self.root, base_sha=self.sha)
        self.assertEqual(out["stage"], "pre_executor")
        self.assertFalse(out.get("patch_scope_verified"))

    def test_lease_contention_while_prior_issue_held(self):
        store = MemoryGitRef()
        Controller(store).acquire(
            request_id_for(216),
            "https://github.com/DaniilSydorenko/haversine-geolocation/issues/216",
        )
        trusted = trusted_attestation_from_store(store, 217)
        out = self._run(217, store=store, prior_proofs=(_good_proof(0),), trusted=trusted)
        self.assertEqual(out["reason"], "lease_contention")

    def test_ci_pending_not_pass(self):
        out = self._run(216, ci=CiEvidence("PENDING", "SUCCESS"))
        self.assertEqual(out["reason"], "ci_evidence_incomplete")

    def test_ci_unknown_not_pass(self):
        out = self._run(216, ci=CiEvidence("UNKNOWN", "UNKNOWN"))
        self.assertEqual(out["reason"], "ci_evidence_incomplete")

    def test_publisher_idempotency_duplicate_branch(self):
        self.assertEqual(
            publisher_precheck(base_sha=self.sha, issue=216, existing_branch_pr=True)["reason"],
            "duplicate_pr_for_issue_branch",
        )

    def test_inventory_queue_mismatch(self):
        bad = {**self.inventory, "issues": []}
        store = MemoryGitRef()
        req = VerticalRequest(216, "1", bad, trusted=trusted_bundle(store), budget=BUDGET_OK)
        out = run_offline_vertical(
            req, lease_store=store, workspace=self.root, base_sha=self.sha, apply_agent_change=_write_allowed,
        )
        self.assertEqual(out["reason"], "queue_mismatch")

    def test_admission_fail_closed_shape(self):
        """Trusted + budget with executor still never authorizes live model."""
        store = MemoryGitRef()
        admission = evaluate_before_model_handoff(
            216, "999002", trusted_attestation=trusted_bundle(store), budget_attestation=BUDGET_OK,
        )
        self.assertEqual(admission["decision"], "STOP")
        self.assertFalse(admission["model_credential_handoff"])


if __name__ == "__main__":
    unittest.main()