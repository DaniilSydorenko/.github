"""Offline negative tests for the #164 lease-to-OpenHands admission adapter."""
from __future__ import annotations

import importlib.util
import unittest
from dataclasses import replace
from unittest.mock import patch

from github_ref_lease import Controller, agent_id_for
from test_github_ref_lease import MemoryGitRef

import openhands_lease_admission_adapter as adapter
from openhands_lease_admission_adapter import (
    AdmissionRequest,
    LeaseRefEvidence,
    RulesetEvidence,
    TargetHeadEvidence,
    WriterIdentityEvidence,
    evaluate_admission,
    request_id_for,
)

from test_lease_ruleset_candidate import APP_ID, BRANCH, GUARD, UPDATE

HAVERSINE = "https://github.com/DaniilSydorenko/haversine-geolocation"
HAS_PRECONDITIONS = importlib.util.find_spec("openhands_164_lease_preconditions") is not None


def reserved_snapshot(store: MemoryGitRef, issue: int) -> dict:
    rid = request_id_for(issue)
    assert Controller(store).acquire(rid, f"{HAVERSINE}/issues/{issue}") == "ACQUIRED"
    return store.read().state


def good_bundle(
    store: MemoryGitRef,
    *,
    issue: int = 216,
    head: str = "a" * 40,
    lease_head: str = "b" * 40,
) -> AdmissionRequest:
    state = reserved_snapshot(store, issue)
    writer = agent_id_for(request_id_for(issue))
    return AdmissionRequest(
        issue=issue,
        workflow_run_id="123456",
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


class AdapterNegativeTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryGitRef()

    def test_unknown_issue_stops(self):
        bundle = good_bundle(self.store)
        verdict = evaluate_admission(replace(bundle, issue=999))
        self.assertEqual(verdict["reason"], "issue_out_of_scope")

    def test_stale_default_head_stops(self):
        bundle = good_bundle(self.store)
        bundle = replace(
            bundle,
            target_head=TargetHeadEvidence("a" * 40, "a" * 40, "c" * 40, True),
        )
        self.assertEqual(evaluate_admission(bundle)["reason"], "default_head_changed_during_admission")

    def test_replayed_target_sha_stops(self):
        bundle = good_bundle(self.store)
        bundle = replace(
            bundle,
            target_head=TargetHeadEvidence("d" * 40, "a" * 40, "a" * 40, True),
        )
        self.assertEqual(evaluate_admission(bundle)["reason"], "stale_or_replayed_target_sha")

    def test_unauthenticated_head_stops(self):
        bundle = good_bundle(self.store)
        bundle = replace(
            bundle,
            target_head=TargetHeadEvidence("a" * 40, "a" * 40, "a" * 40, False),
        )
        self.assertEqual(evaluate_admission(bundle)["reason"], "target_head_not_authenticated")

    def test_lease_ref_stale_stops(self):
        bundle = good_bundle(self.store)
        bundle = replace(bundle, expected_lease_sha="c" * 40)
        self.assertEqual(evaluate_admission(bundle)["reason"], "lease_ref_sha_missing_or_stale")

    def test_snapshot_head_mismatch_stops(self):
        bundle = good_bundle(self.store)
        bundle = replace(
            bundle,
            lease=replace(bundle.lease, snapshot_commit_sha="d" * 40),
        )
        self.assertEqual(evaluate_admission(bundle)["reason"], "lease_ref_head_snapshot_mismatch")

    def test_writer_identity_mismatch_stops(self):
        bundle = good_bundle(self.store)
        bundle = replace(bundle, writer=WriterIdentityEvidence("bc-wrong", True))
        self.assertEqual(evaluate_admission(bundle)["reason"], "writer_identity_mismatch")

    def test_writer_attestation_missing_stops(self):
        bundle = good_bundle(self.store)
        bundle = replace(
            bundle,
            writer=WriterIdentityEvidence(agent_id_for(request_id_for(216)), False),
        )
        self.assertEqual(evaluate_admission(bundle)["reason"], "writer_attestation_missing")

    def test_ruleset_stop_maps_to_immutable_unknown(self):
        bundle = good_bundle(self.store)
        bundle = replace(
            bundle,
            ruleset=RulesetEvidence({**BRANCH, "protected": False}, [UPDATE, GUARD], APP_ID, True),
        )
        verdict = evaluate_admission(bundle)
        self.assertEqual(verdict["reason"], "immutable_ref_protection_unknown")

    def test_ruleset_non_candidate_status_stops(self):
        bundle = good_bundle(self.store)
        with patch.object(adapter, "ruleset_audit", return_value={"status": "PREPARED"}):
            self.assertEqual(
                evaluate_admission(bundle)["reason"],
                "ruleset_audit_status_not_candidate",
            )

    def test_ruleset_inventory_incomplete_stops(self):
        bundle = good_bundle(self.store)
        bundle = replace(bundle, ruleset=RulesetEvidence(BRANCH, [UPDATE, GUARD], APP_ID, False))
        self.assertEqual(evaluate_admission(bundle)["reason"], "ruleset_inventory_incomplete")

    def test_missing_ruleset_stops_before_deeper_checks(self):
        bundle = good_bundle(self.store)
        bundle = replace(bundle, ruleset=None)
        with patch.object(adapter, "validate_lease_snapshot") as mock_validate:
            verdict = evaluate_admission(bundle)
        self.assertEqual(verdict["reason"], "ruleset_evidence_missing")
        mock_validate.assert_not_called()

    def test_fail_fast_target_head_before_lease_alignment(self):
        bundle = good_bundle(self.store)
        bundle = replace(
            bundle,
            target_head=TargetHeadEvidence("a" * 40, "a" * 40, "a" * 40, False),
        )
        with patch.object(adapter, "check_state", side_effect=AssertionError("must not run")):
            self.assertEqual(evaluate_admission(bundle)["reason"], "target_head_not_authenticated")

    def test_operational_security_false_stops(self):
        bundle = good_bundle(self.store)
        bundle = replace(bundle, lease=replace(bundle.lease, exclusive_writer_verified=False))
        self.assertEqual(evaluate_admission(bundle)["reason"], "operational_security_not_verified")

    @unittest.skipUnless(HAS_PRECONDITIONS, "openhands_164_lease_preconditions lands in #166")
    def test_full_shape_ok_still_not_live_authorization(self):
        verdict = evaluate_admission(good_bundle(self.store))
        self.assertEqual(verdict["decision"], "STOP")
        self.assertEqual(
            verdict["reason"],
            "openhands_admission_preconditions_shape_ok_not_live_authorization",
        )
        self.assertFalse(verdict["openhands_authorized"])

    @unittest.skipUnless(HAS_PRECONDITIONS, "openhands_164_lease_preconditions lands in #166")
    def test_wrong_phase_stops_via_preconditions(self):
        bundle = good_bundle(self.store)
        state = {**bundle.lease.state, "phase": "DISPATCHING"}
        bundle = replace(bundle, lease=replace(bundle.lease, state=state))
        self.assertEqual(evaluate_admission(bundle)["reason"], "lease_not_reserved")

    def test_missing_preconditions_module_stops(self):
        if HAS_PRECONDITIONS:
            self.skipTest("preconditions module present")
        bundle = good_bundle(self.store)
        verdict = evaluate_admission(bundle)
        self.assertEqual(verdict["reason"], "lease_preconditions_module_unavailable")

    def test_dispatching_phase_with_mocked_preconditions(self):
        bundle = good_bundle(self.store)
        with patch.object(adapter, "validate_lease_snapshot", side_effect=adapter.AdmissionDenied("lease_not_reserved")):
            self.assertEqual(evaluate_admission(bundle)["reason"], "lease_not_reserved")

    def test_unexpected_precondition_exception_fails_closed(self):
        bundle = good_bundle(self.store)
        with patch.object(adapter, "validate_lease_snapshot", side_effect=ValueError("synthetic fault")):
            verdict = evaluate_admission(bundle)
        self.assertEqual(verdict["decision"], "STOP")
        self.assertEqual(verdict["reason"], "admission_precondition_error")

    def test_untrusted_request_object_stops(self):
        verdict = evaluate_admission(None)  # type: ignore[arg-type]
        self.assertEqual(verdict["reason"], "untrusted_admission_request")


if __name__ == "__main__":
    unittest.main()