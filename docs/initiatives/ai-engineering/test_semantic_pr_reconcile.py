"""Synthetic semantic cases; no private career records or GitHub writes."""
from copy import deepcopy
import unittest

from semantic_pr_reconcile import reconcile_one

A, B, C = "a" * 40, "b" * 40, "c" * 40
REPO = "DaniilSydorenko/example"
ISSUE = f"https://github.com/{REPO}/issues/42"


def evidence(prs=None):
    return {
        "schema_version": 1,
        "repository": REPO,
        "issue_number": 42,
        "issue_url": ISSUE,
        "issue_state": "open",
        "inventory_complete": True,
        "semantic_attestations_complete": True,
        "default_sha": A,
        "observed_default_sha": A,
        "permission": "granted",
        "owner_gate": False,
        "writer": "idle",
        "proposed_paths": ["src/feature.ts"],
        "prs": [] if prs is None else prs,
    }


def pr(number=212, relation="PARTIAL", *, path="src/feature.ts"):
    return {
        "number": number, "url": f"https://github.com/{REPO}/pull/{number}",
        "state": "open", "merged": False,
        "head_sha": B, "observed_head_sha": B,
        "base_sha": A, "observed_base_sha": A,
        "changed_paths_complete": True, "changed_paths": [path],
        "relation": relation, "reviewer_confirmed": True,
        "owner_gate": False, "writer_active": False,
        "stack_parent": None,
    }


class SemanticReconcileTests(unittest.TestCase):
    def verdict(self, sample):
        r = reconcile_one(sample)
        self.assertIs(r["launched"], False)
        self.assertIs(r["execution_authorized"], False)
        self.assertIs(r["advisory_only"], True)
        return r["action"], r["reason"]

    def test_ladvero_existing_partial_pr_reused(self):
        self.assertEqual(self.verdict(evidence([pr()]))[0], "REUSE_EXISTING_PR")

    def test_ladvero_proposed_not_accepted_reused(self):
        self.assertEqual(self.verdict(evidence([pr(relation="PROPOSED_NOT_ACCEPTED")]))[0],
                         "REUSE_EXISTING_PR")

    def test_empty_scoped_inventory_is_candidate_not_launch(self):
        self.assertEqual(self.verdict(evidence())[0], "READY_FOR_OWNER_DISPATCH")

    def test_unrelated_pr_nonoverlapping_does_not_freeze_domain(self):
        p = pr(65, "UNRELATED", path="docs/unrelated.md")
        p["owner_gate"] = True
        self.assertEqual(self.verdict(evidence([p]))[0], "READY_FOR_OWNER_DISPATCH")

    def test_unrelated_but_same_file_blocks_new_code(self):
        self.assertEqual(self.verdict(evidence([pr(216, "UNRELATED")]))[0],
                         "WAIT_DEPENDENCY")

    def test_unrelated_open_stack_parent_blocks(self):
        p = pr(91, "UNRELATED", path="docs/different.md")
        p["stack_parent"] = 64
        self.assertEqual(self.verdict(evidence([p]))[0], "WAIT_DEPENDENCY")

    def test_incomplete_semantic_inventory_fails_closed(self):
        x = evidence()
        x["semantic_attestations_complete"] = False
        self.assertEqual(self.verdict(x)[0], "STOP")

    def test_unknown_relation_fails_closed(self):
        self.assertEqual(self.verdict(evidence([pr(relation="looks_similar")]))[0], "STOP")
        self.assertEqual(self.verdict(evidence([pr(relation="INSUFFICIENT_EVIDENCE")]))[0], "STOP")

    def test_reviewers_required_not_inferred_from_filename(self):
        p = pr()
        p["reviewer_confirmed"] = False
        self.assertEqual(self.verdict(evidence([p]))[0], "STOP")

    def test_changed_pr_head_fails_closed(self):
        p = pr()
        p["observed_head_sha"] = C
        self.assertEqual(self.verdict(evidence([p]))[0], "STOP")

    def test_changed_pr_base_fails_closed(self):
        p = pr()
        p["observed_base_sha"] = C
        self.assertEqual(self.verdict(evidence([p]))[0], "STOP")

    def test_changed_default_branch_fails_closed(self):
        x = evidence()
        x["observed_default_sha"] = C
        self.assertEqual(self.verdict(x)[0], "STOP")

    def test_duplicate_pr_identity_fails_closed(self):
        self.assertEqual(self.verdict(evidence([pr(), deepcopy(pr())]))[0], "STOP")

    def test_missing_owner_permission(self):
        x = evidence()
        x["permission"] = "missing"
        self.assertEqual(self.verdict(x)[0], "OWNER_GATE")

    def test_owner_publication_gate(self):
        x = evidence()
        x["owner_gate"] = True
        self.assertEqual(self.verdict(x)[0], "OWNER_GATE")

    def test_unknown_writer_fails_closed(self):
        x = evidence()
        x["writer"] = "unknown"
        self.assertEqual(self.verdict(x)[0], "STOP")

    def test_active_writer_waits(self):
        x = evidence()
        x["writer"] = "active"
        self.assertEqual(self.verdict(x)[0], "WAIT_DEPENDENCY")

    def test_existing_pr_other_writer_waits(self):
        p = pr()
        p["writer_active"] = True
        self.assertEqual(self.verdict(evidence([p]))[0], "WAIT_DEPENDENCY")

    def test_existing_pr_owner_gate(self):
        p = pr()
        p["owner_gate"] = True
        self.assertEqual(self.verdict(evidence([p]))[0], "OWNER_GATE")

    def test_handbook_stack_waits_for_parent(self):
        p = pr(91)
        p["stack_parent"] = 64
        self.assertEqual(self.verdict(evidence([p]))[0], "WAIT_DEPENDENCY")

    def test_multiple_competing_existing_prs_stop(self):
        self.assertEqual(self.verdict(evidence([pr(212), pr(216)]))[0], "STOP")

    def test_closed_unmerged_same_outcome_is_not_new_work_permission(self):
        p = pr(190, "PROPOSED_NOT_ACCEPTED")
        p.update(state="closed", merged=False)
        self.assertEqual(self.verdict(evidence([p]))[0], "STOP")

    def test_overlapping_unrelated_pr_blocks_reuse(self):
        p = pr(212, "PARTIAL")
        other = pr(216, "UNRELATED", path="src/feature.ts")
        self.assertEqual(self.verdict(evidence([p, other]))[0], "WAIT_DEPENDENCY")

    def test_existing_pr_with_independent_unrelated_pr_still_reused(self):
        p = pr(212, "PARTIAL")
        other = pr(216, "UNRELATED", path="docs/unrelated.md")
        self.assertEqual(self.verdict(evidence([p, other]))[0], "REUSE_EXISTING_PR")

    def test_haversine_owner_verified_accepted_outcome(self):
        p = pr(190, "EXACT_SAME_OUTCOME")
        p.update(state="closed", merged=True, accepted_commit=C,
                 accepted_on_default=True,
                 accepted_proof=f"https://github.com/{REPO}/commit/{C}")
        self.assertEqual(self.verdict(evidence([p]))[0], "NO_READY_WORK")

    def test_merged_not_proof_without_default_acceptance(self):
        p = pr(190, "EXACT_SAME_OUTCOME")
        p.update(state="closed", merged=True, accepted_commit=C,
                 accepted_on_default=False,
                 accepted_proof=f"https://github.com/{REPO}/pull/190")
        self.assertEqual(self.verdict(evidence([p]))[0], "STOP")

    def test_owner_supersession_requires_proof(self):
        p = pr(190, "SUPERSEDED_BY_OWNER")
        self.assertEqual(self.verdict(evidence([p]))[0], "OWNER_GATE")

    def test_owner_superseded_but_not_merged(self):
        p = pr(190, "SUPERSEDED_BY_OWNER")
        p["owner_supersession_approved"] = True
        self.assertEqual(self.verdict(evidence([p]))[0], "WAIT_DEPENDENCY")

    def test_career_private_cross_repo_reference_stops(self):
        p = pr()
        p["url"] = "https://github.com/Other/secret/pull/212"
        self.assertEqual(self.verdict(evidence([p]))[0], "STOP")

    def test_closed_issue_not_proof_of_release(self):
        x = evidence()
        x["issue_state"] = "closed"
        self.assertEqual(self.verdict(x)[0], "STOP")

    def test_invalid_path_cannot_claim_independence(self):
        x = evidence()
        x["proposed_paths"] = ["../private/password.txt"]
        self.assertEqual(self.verdict(x)[0], "STOP")

    def test_missing_required_pr_observation(self):
        p = pr()
        p.pop("changed_paths_complete")
        self.assertEqual(self.verdict(evidence([p]))[0], "STOP")

    def test_age_not_a_signal(self):
        p = pr()
        p["opened_year"] = 2019
        self.assertEqual(self.verdict(evidence([p]))[0], "REUSE_EXISTING_PR")


if __name__ == "__main__":
    unittest.main()
