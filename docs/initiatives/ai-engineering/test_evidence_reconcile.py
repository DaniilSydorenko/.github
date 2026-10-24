"""Synthetic-only tests. Not a live GitHub API or semantic matching test."""
import unittest

from evidence_reconcile import reconcile

A = 'a' * 40
B = 'b' * 40


def fixture():
    return {
        'task': {
            'schema_version': 1, 'repository': 'example/test',
            'issue': 'https://github.com/example/test/issues/42',
            'evidence': {
                'default_sha': A, 'checked_sha': A, 'inventory_complete': True,
                'issue_state': 'open', 'accepted_commit': None, 'accepted_proof': None,
                'related_prs': [], 'dependencies': [], 'writer': 'idle',
                'scope': 'allowed', 'owner_permission': 'granted',
                'owner_gate': False, 'external': 'clear'
            },
        },
        'observed': {
            'repo': 'example/test', 'issue_number': 42, 'issue_state': 'open',
            'default_sha': A, 'related_inventory_complete': True,
            'related_prs': [], 'accepted_shas': [],
        },
    }


class EvidenceReconcileTests(unittest.TestCase):
    def test_clean_candidate_remains_only_advisory(self):
        r = reconcile(fixture())
        self.assertEqual(r['status'], 'READY')
        self.assertEqual(r['verification'], 'CONSISTENT_ONLY')
        self.assertFalse(r['launched'])

    def test_changed_default_sha(self):
        x = fixture(); x['observed']['default_sha'] = B
        self.assertEqual(reconcile(x)['status'], 'NEEDS_EVIDENCE')

    def test_wrong_issue_or_repo(self):
        x = fixture(); x['observed']['issue_number'] = 43
        self.assertEqual(reconcile(x)['status'], 'NEEDS_EVIDENCE')
        x = fixture(); x['observed']['repo'] = 'other/repo'
        self.assertEqual(reconcile(x)['status'], 'NEEDS_EVIDENCE')

    def test_closed_issue_state_changed(self):
        x = fixture(); x['observed']['issue_state'] = 'closed'
        self.assertEqual(reconcile(x)['status'], 'NEEDS_EVIDENCE')

    def test_partial_inventory(self):
        x = fixture(); x['observed']['related_inventory_complete'] = False
        self.assertEqual(reconcile(x)['status'], 'NEEDS_EVIDENCE')

    def test_unclassified_pr_is_not_unrelated(self):
        x = fixture(); x['observed']['related_prs'] = [{'number': 17, 'head_sha': B, 'state': 'open'}]
        self.assertEqual(reconcile(x)['status'], 'NEEDS_EVIDENCE')

    def test_declared_pr_head_changed(self):
        x = fixture()
        x['task']['evidence']['related_prs'] = [{'number': 17, 'head_sha': A, 'relation': 'same_outcome'}]
        x['observed']['related_prs'] = [{'number': 17, 'head_sha': B, 'state': 'open'}]
        self.assertEqual(reconcile(x)['status'], 'NEEDS_EVIDENCE')

    def test_merged_pr_cannot_be_treated_as_open(self):
        x = fixture()
        x['task']['evidence']['related_prs'] = [{'number': 17, 'head_sha': B, 'relation': 'same_outcome'}]
        x['observed']['related_prs'] = [{'number': 17, 'head_sha': B, 'state': 'closed'}]
        self.assertEqual(reconcile(x)['status'], 'NEEDS_EVIDENCE')

    def test_consistent_existing_pr_not_reimplemented(self):
        x = fixture()
        x['task']['evidence']['related_prs'] = [{'number': 17, 'head_sha': B, 'relation': 'same_outcome'}]
        x['observed']['related_prs'] = [{'number': 17, 'head_sha': B, 'state': 'open'}]
        self.assertEqual(reconcile(x)['status'], 'EXISTING_PR')

    def test_unseen_accepted_commit_is_not_done(self):
        x = fixture()
        x['task']['evidence']['accepted_commit'] = B
        x['task']['evidence']['accepted_proof'] = 'https://github.com/example/test/pull/18'
        self.assertEqual(reconcile(x)['status'], 'NEEDS_EVIDENCE')

    def test_accepted_commit_observed_is_only_consistent(self):
        x = fixture()
        x['task']['evidence']['accepted_commit'] = B
        x['task']['evidence']['accepted_proof'] = 'https://github.com/example/test/pull/18'
        x['observed']['accepted_shas'] = [B]
        self.assertEqual(reconcile(x)['status'], 'ALREADY_ACCEPTED')

    def test_unseen_supersession_is_not_done(self):
        x = fixture()
        x['task']['evidence']['superseded_by'] = {
            'accepted_sha': B, 'ref': 'https://github.com/example/test/pull/19', 'reason': 'Owner chose 2.0.1'
        }
        self.assertEqual(reconcile(x)['status'], 'NEEDS_EVIDENCE')

    def test_seen_supersession_is_distinct(self):
        x = fixture()
        x['task']['evidence']['superseded_by'] = {
            'accepted_sha': B, 'ref': 'https://github.com/example/test/pull/19', 'reason': 'Owner chose 2.0.1'
        }
        x['observed']['accepted_shas'] = [B]
        self.assertEqual(reconcile(x)['status'], 'SUPERSEDED')

    def test_malformed_or_duplicate_observation(self):
        x = fixture(); x['observed']['related_prs'] = [
            {'number': 17, 'head_sha': B, 'state': 'open'},
            {'number': 17, 'head_sha': B, 'state': 'open'}]
        self.assertEqual(reconcile(x)['status'], 'NEEDS_EVIDENCE')

    def test_missing_observation(self):
        x = fixture(); del x['observed']
        self.assertEqual(reconcile(x)['status'], 'NEEDS_EVIDENCE')


if __name__ == '__main__':
    unittest.main()
