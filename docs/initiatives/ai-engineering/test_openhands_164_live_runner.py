"""Regression tests for #164 live runner lease cleanup and attestation gates."""
from __future__ import annotations

import os
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from github_ref_lease import Controller
from openhands_164_live_runner import APPROVED_OPERATION, EXACT_HEAD_CI_PENDING, run_pilot
from openhands_164_live_wiring import CONTROL_ACTOR, CONTROL_REPO
from openhands_164_live_runner import TARGET_REPO
from openhands_164_patch_contract import ALLOWED
from openhands_lease_admission_adapter import request_id_for
from test_github_ref_lease import MemoryGitRef


def _env(**extra):
    base = {
        "GITHUB_REPOSITORY": CONTROL_REPO,
        "GITHUB_ACTOR": CONTROL_ACTOR,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ATTEMPT": "1",
        "AI_ENG_APPROVED_OPERATION": APPROVED_OPERATION,
        "AI_ENG_OWNER_GO_ISSUE": "216",
        "GH_TOKEN": "read-token",
        "AI_ENG_LEASE_WRITER_TOKEN": "lease-token",
        "OPENROUTER_API_KEY": "sk-or-offline-fixture",
        "GITHUB_RUN_ID": "4242",
    }
    base.update(extra)
    return base


def _satisfied_repo() -> pathlib.Path:
    tmp = tempfile.mkdtemp()
    bare = pathlib.Path(tmp) / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(bare)], check=True)
    root = pathlib.Path(tmp) / "target"
    root.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "master", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "remote", "add", "origin", f"https://github.com/{TARGET_REPO}"],
        check=True,
    )
    doc = root / ALLOWED[216]
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# Runtime Compatibility\nNode 22 Supported Node 24 Supported Node 26 smoke\n"
        "minimum supported Node.js version\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "-C", str(root), "add", ALLOWED[216]],
        check=True,
    )
    subprocess.run(
        [
            "git", "-C", str(root), "-c", "user.name=T", "-c", "user.email=t@e",
            "commit", "-qm", "doc",
        ],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "push", str(bare), "master"], check=True)
    return root, bare


class LiveRunnerRegressionTests(unittest.TestCase):
    def test_early_already_satisfied_skips_lease_and_budget(self):
        root, bare = _satisfied_repo()
        sha = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
        inv = {
            "reason": "live_authorization_not_integrated",
            "default_head": sha,
            "issues": [{"number": 216, "target": "docs/compatibility.md"}],
        }
        real_check_output = subprocess.check_output

        def ls_remote_stub(cmd, **kwargs):
            if "ls-remote" in cmd:
                if kwargs.get("text"):
                    return f"{sha}\trefs/heads/master\n"
                return f"{sha}\trefs/heads/master\n".encode()
            return real_check_output(cmd, **kwargs)

        with patch.dict(os.environ, _env(), clear=True), patch(
            "openhands_164_live_runner.inventory_inspect", return_value=inv
        ), patch("openhands_164_live_runner.subprocess.check_output", side_effect=ls_remote_stub):
            out = run_pilot(root, live_attested=False)
        self.assertEqual(out["reason"], "ALREADY_SATISFIED")
        self.assertTrue(out.get("satisfaction_pinned_to_remote_master"))
        self.assertEqual(out.get("base_sha"), sha)
        self.assertFalse(out.get("lease_acquired"))
        self.assertFalse(out["model_invoked"])
        self.assertFalse(out["github_write"])

    def test_missing_lease_writer_token_never_acquires(self):
        inv = {
            "reason": "live_authorization_not_integrated",
            "default_head": "a" * 40,
            "issues": [{"number": 216, "target": "docs/compatibility.md"}],
        }
        with patch.dict(os.environ, _env(AI_ENG_LEASE_WRITER_TOKEN="", AI_ENG_LEASE_TOKEN=""), clear=True), patch(
            "openhands_164_live_runner.inventory_inspect", return_value=inv
        ), patch("openhands_164_live_runner.early_readonly_satisfaction_pinned", return_value=None):
            out = run_pilot(".", live_attested=False)
        self.assertEqual(out["reason"], "lease_writer_token_missing")

    def test_live_requires_g3_attestation(self):
        inv = {"reason": "live_authorization_not_integrated", "default_head": "a" * 40}
        with patch.dict(os.environ, _env(), clear=True), patch(
            "openhands_164_live_runner.inventory_inspect", return_value=inv
        ), patch("openhands_164_live_runner.GitHubRefStore") as store:
            out = run_pilot(".", live_attested=True)
            self.assertEqual(out["reason"], "g3_isolated_evidence_invalid")
            store.assert_not_called()

    def test_isolated_g3_binding_and_credential_rejection(self):
        from openhands_164_production_gates import verify_isolated_g3_evidence, _g3_binding, _G3_REASON
        env = _env(AI_ENG_WRITER_APP_ID="5535339", AI_ENG_OWNER_GO_ISSUE="217",
                   GITHUB_SHA="a" * 40)
        with patch.dict(os.environ, env, clear=True):
            evidence = {**_g3_binding(217), "audit": {
                "status": "CANDIDATE", "reason": _G3_REASON, "candidate_only": True,
                "cursor_launch_authorized": False, "model_runs_started": 0,
                "github_mutated": False}}
            os.environ["AI_ENG_G3_EVIDENCE"] = json.dumps(evidence)
            self.assertIsNone(verify_isolated_g3_evidence(217))
            for key, value in (("run_id", "999"), ("attempt", 2), ("sha", "b" * 40),
                               ("repository", "other/repo"), ("issue", 226),
                               ("writer_app_id", 1), ("audit", True)):
                with self.subTest(key=key):
                    os.environ["AI_ENG_G3_EVIDENCE"] = json.dumps({**evidence, key: value})
                    self.assertEqual(verify_isolated_g3_evidence(217)["reason"],
                                     "g3_isolated_evidence_invalid")
            for raw in ("", "{", "true"):
                os.environ["AI_ENG_G3_EVIDENCE"] = raw
                self.assertIsNotNone(verify_isolated_g3_evidence(217))
            os.environ["AI_ENG_G3_EVIDENCE"] = json.dumps(evidence)
            os.environ["AI_ENG_RULESET_AUDIT_TOKEN"] = "must-not-be-present"
            self.assertEqual(verify_isolated_g3_evidence(217)["reason"],
                             "privileged_audit_token_in_live_runner")

    def test_stale_workspace_releases_lease(self):
        from openhands_runner_admission_bridge import ProviderBudgetAttestation

        store = MemoryGitRef()
        inv = {
            "reason": "live_authorization_not_integrated",
            "default_head": "a" * 40,
            "issues": [{"number": 216, "target": "docs/compatibility.md"}],
        }
        with patch.dict(os.environ, _env(), clear=True), patch(
            "openhands_164_live_runner.inventory_inspect", return_value=inv
        ), patch("openhands_164_live_runner.early_readonly_satisfaction_pinned", return_value=None), patch(
            "openhands_164_live_runner.GitHubRefStore", return_value=store
        ), patch(
            "openhands_164_live_runner._validate_target_workspace",
            side_effect=PermissionError("stale_target_base"),
        ):
            out = run_pilot(".", live_attested=False)
        self.assertEqual(out["reason"], "stale_target_base")
        self.assertTrue(out.get("lease_cleanup", {}).get("released"))
        self.assertEqual(store.read().state["phase"], "IDLE")

    def test_collision_query_failure_releases_lease(self):
        store = MemoryGitRef()
        inv = {
            "reason": "live_authorization_not_integrated",
            "default_head": "a" * 40,
            "issues": [{"number": 216, "target": "docs/compatibility.md"}],
        }
        with patch.dict(os.environ, _env(), clear=True), patch(
            "openhands_164_live_runner.inventory_inspect", return_value=inv
        ), patch("openhands_164_live_runner.early_readonly_satisfaction_pinned", return_value=None), patch(
            "openhands_164_live_runner.GitHubRefStore", return_value=store
        ), patch(
            "openhands_164_live_runner._validate_target_workspace", return_value=None
        ), patch(
            "openhands_164_live_runner._github_transport", side_effect=OSError("network")
        ):
            out = run_pilot(".", live_attested=False)
        self.assertEqual(out["reason"], "collision_query_failed")
        self.assertTrue(out.get("lease_cleanup", {}).get("released"))

    def test_exact_head_ci_pending_handoff(self):
        published = {
            "decision": "STOP",
            "reason": "live_164_draft_pr_published_pending_ci",
            "pr_url": "https://github.com/DaniilSydorenko/haversine-geolocation/pull/77",
            "model_invoked": True,
            "github_write": True,
            "lease_phase": "VERIFYING",
        }
        from openhands_164_live_runner import _attach_exact_head_ci
        from openhands_164_vertical_integration import CiEvidence

        with patch(
            "openhands_164_live_runner.exact_head_ci_from_check_runs",
            return_value=(CiEvidence("PENDING", "PENDING"), None),
        ):
            out = _attach_exact_head_ci(published.copy(), read_token="x")
        self.assertEqual(out["reason"], EXACT_HEAD_CI_PENDING)
        self.assertFalse(out["ci_verified"])
        self.assertFalse(out["pilot_complete"])


if __name__ == "__main__":
    unittest.main()