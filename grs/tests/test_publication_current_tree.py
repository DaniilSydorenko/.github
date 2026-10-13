#!/usr/bin/env python3
"""Regression coverage for current source-tree publication evidence."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDITOR = ROOT / "grs/publication/audit_current_tree.py"
SHA = "a" * 40
BASE = {
    "repository": "DaniilSydorenko/test",
    "sensitive_surfaces": [
        {"path": ".local/migration/", "disposition": "private-runtime"},
        {"path": "private/", "disposition": "externalize"},
    ],
}


class CurrentTreeTests(unittest.TestCase):
    def audit(self, paths, *, tree_override=None, manifest_override=None):
        with tempfile.TemporaryDirectory() as tmp:
            tree = {"sha": SHA, "truncated": False, "tree": [
                {"path": p, "type": "blob", "sha": SHA} for p in paths
            ]}
            tree = tree if tree_override is None else tree_override
            m = BASE if manifest_override is None else manifest_override
            a, b = Path(tmp) / "tree.json", Path(tmp) / "manifest.json"
            a.write_text(json.dumps(tree))
            b.write_text(json.dumps(m))
            return subprocess.run([sys.executable, str(AUDITOR), str(a), str(b)],
                                  check=False, capture_output=True, text=True)

    def test_real_hidden_private_runtime_match_requires_review(self):
        r = self.audit([".local/migration/raw.xlsx", "src/index.ts"])
        self.assertEqual(r.returncode, 2, r.stderr)
        result = json.loads(r.stdout)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["matching_blobs"], 1)
        self.assertFalse(result["history_audited"])
        self.assertFalse(result["publication_authorized"])

    def test_non_hidden_similar_name_does_not_false_match(self):
        r = self.audit(["local/migration/raw.xlsx", "src/index.ts"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(json.loads(r.stdout)["matching_blobs"], 0)

    def test_no_match_not_mistaken_for_publication_approval(self):
        r = self.audit(["src/index.ts"])
        self.assertEqual(r.returncode, 0)
        output = json.loads(r.stdout)
        self.assertEqual(output["status"], "NO_DECLARED_CURRENT_TREE_PATH_MATCH")
        self.assertFalse(output["history_audited"])
        self.assertFalse(output["contents_audited"])

    def test_truncated_snapshot_never_passes(self):
        r = self.audit([], tree_override={"sha": SHA, "truncated": True, "tree": []})
        self.assertEqual(r.returncode, 1)
        self.assertEqual(json.loads(r.stdout)["status"], "INVALID")

    def test_missing_sha_never_passes(self):
        r = self.audit([], tree_override={"truncated": False, "tree": []})
        self.assertEqual(r.returncode, 1)

    def test_empty_tree_is_unknown_not_clean(self):
        r = self.audit([])
        self.assertEqual(r.returncode, 1)
        self.assertEqual(json.loads(r.stdout)["status"], "UNKNOWN")

    def test_parent_traversal_surface_rejected(self):
        m = {"sensitive_surfaces": [{"path": "../private/", "disposition": "review"}]}
        r = self.audit(["src/index.ts"], manifest_override=m)
        self.assertEqual(r.returncode, 1)

    def test_unsupported_disposition_rejected(self):
        m = {"sensitive_surfaces": [{"path": "private/", "disposition": "ignored"}]}
        r = self.audit(["src/index.ts"], manifest_override=m)
        self.assertEqual(r.returncode, 1)

    def test_duplicate_relative_alias_rejected(self):
        m = {"sensitive_surfaces": [
            {"path": "private/", "disposition": "review"},
            {"path": "./private/", "disposition": "review"},
        ]}
        r = self.audit(["src/index.ts"], manifest_override=m)
        self.assertEqual(r.returncode, 1)

    def test_prefix_does_not_match_neighbor_name(self):
        r = self.audit(["private2/file.txt", "src/index.ts"])
        self.assertEqual(r.returncode, 0)

    def test_matched_paths_are_not_echoed_to_output(self):
        r = self.audit(["private/very-personal-file-name.txt", "src/index.ts"])
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("very-personal-file-name", r.stdout)


if __name__ == "__main__":
    unittest.main()
