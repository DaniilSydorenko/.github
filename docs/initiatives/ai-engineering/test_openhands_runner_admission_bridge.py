"""Offline tests for trusted-runner → evaluate_admission bridge (#164 D2)."""
from __future__ import annotations

import importlib.util
import unittest
from dataclasses import replace
from unittest.mock import patch

from github_ref_lease import Controller, agent_id_for
from test_github_ref_lease import MemoryGitRef
from test_lease_ruleset_candidate import APP_ID, BRANCH, GUARD, UPDATE

from openhands_lease_admission_adapter import (
    LeaseRefEvidence,
    RulesetEvidence,
    TargetHeadEvidence,
    WriterIdentityEvidence,
    request_id_for,
)
from openhands_runner_admission_bridge import (
    ProviderBudgetAttestation,
    TrustedWorkflowAttestation,
    evaluate_before_model_handoff,
    finalize_pre_model_handoff,
)

HAVERSINE = "https://github.com/DaniilSydorenko/haversine-geolocation"
HAS_PRECONDITIONS = importlib.util.find_spec("openhands_164_lease_preconditions") is not None

BUDGET_OK = ProviderBudgetAttestation(
    verified_within_shared_cap=True,
    attestation_source="trusted_workflow_budget_probe",
)


def trusted_bundle(store: MemoryGitRef, *, issue: int = 216) -> TrustedWorkflowAttestation:
    rid = request_id_for(issue)
    assert Controller(store).acquire(rid, f"{HAVERSINE}/issues/{issue}") == "ACQUIRED"
    state = store.read().state
    head = "a" * 40
    lease_head = store.read().sha
    writer = agent_id_for(rid)
    return TrustedWorkflowAttestation(
        expected_lease_sha=lease_head,
        lease=LeaseRefEvidence(
            observed_ref_head_sha=lease_head,
            snapshot_commit_sha=lease_head,
            state=state,
            authenticated_ref=True,
            exclusive_writer_verified=True,
            credential_path_verified=True,
        ),
        target_head=TargetHeadEvidence(head, head, head, True),
        writer=WriterIdentityEvidence(writer, True),
        ruleset=RulesetEvidence(BRANCH, [UPDATE, GUARD], APP_ID, True),
    )


class BridgeNegativeTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryGitRef()

    def test_caller_json_security_flags_rejected(self):
        verdict = evaluate_before_model_handoff(
            216,
            "99",
            trusted_attestation=trusted_bundle(self.store),
            budget_attestation=BUDGET_OK,
            caller_context={"exclusive_writer_verified": True, "note": "runner tried to self-attest"},
        )
        self.assertEqual(verdict["reason"], "caller_attestation_fields_not_trusted")
        self.assertFalse(verdict["model_credential_handoff"])

    def test_missing_trusted_attestation_stops(self):
        self.assertEqual(
            evaluate_before_model_handoff(216, "1", trusted_attestation=None, budget_attestation=BUDGET_OK)["reason"],
            "missing_trusted_workflow_attestation",
        )

    def test_missing_budget_attestation_stops(self):
        self.assertEqual(
            evaluate_before_model_handoff(
                216, "1", trusted_attestation=trusted_bundle(self.store), budget_attestation=None
            )["reason"],
            "missing_provider_budget_attestation",
        )

    def test_budget_not_verified_stops(self):
        budget = ProviderBudgetAttestation(False, "trusted_workflow_budget_probe")
        self.assertEqual(
            evaluate_before_model_handoff(
                216, "1", trusted_attestation=trusted_bundle(self.store), budget_attestation=budget
            )["reason"],
            "provider_budget_not_verified",
        )

    def test_finalize_always_blocks_model_handoff(self):
        verdict = finalize_pre_model_handoff(
            {"decision": "STOP", "reason": "openhands_admission_preconditions_shape_ok_not_live_authorization"}
        )
        self.assertEqual(verdict["reason"], "model_handoff_blocked_live_capability_unverified")
        self.assertFalse(verdict["model_credential_handoff"])

    def test_ruleset_missing_via_adapter_still_no_handoff(self):
        trusted = trusted_bundle(self.store)
        trusted = replace(trusted, ruleset=RulesetEvidence(BRANCH, [UPDATE, GUARD], APP_ID, False))
        verdict = evaluate_before_model_handoff(
            216, "77", trusted_attestation=trusted, budget_attestation=BUDGET_OK
        )
        self.assertEqual(verdict["reason"], "ruleset_inventory_incomplete")
        self.assertFalse(verdict["model_credential_handoff"])


class BridgeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryGitRef()

    @unittest.skipUnless(HAS_PRECONDITIONS, "openhands_164_lease_preconditions lands in #166")
    def test_trusted_shape_ok_still_blocks_model_handoff(self):
        verdict = evaluate_before_model_handoff(
            216,
            "123456",
            trusted_attestation=trusted_bundle(self.store),
            budget_attestation=BUDGET_OK,
            caller_context={"runner_note": "offline fixture"},
        )
        self.assertEqual(verdict["decision"], "STOP")
        self.assertEqual(verdict["reason"], "model_handoff_blocked_live_capability_unverified")
        self.assertFalse(verdict["model_credential_handoff"])
        self.assertFalse(verdict["openhands_authorized"])

    @unittest.skipUnless(HAS_PRECONDITIONS, "openhands_164_lease_preconditions lands in #166")
    def test_bridge_delegates_precondition_denial(self):
        trusted = trusted_bundle(self.store)
        state = {**trusted.lease.state, "phase": "DISPATCHING"}
        trusted = replace(
            trusted,
            lease=replace(trusted.lease, state=state),
        )
        self.assertEqual(
            evaluate_before_model_handoff(
                216, "123456", trusted_attestation=trusted, budget_attestation=BUDGET_OK
            )["reason"],
            "lease_not_reserved",
        )


if __name__ == "__main__":
    unittest.main()