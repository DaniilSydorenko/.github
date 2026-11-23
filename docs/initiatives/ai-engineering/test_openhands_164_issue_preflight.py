"""Pinned satisfaction preflight tests."""
from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest

from openhands_164_issue_preflight import early_readonly_satisfaction_pinned
from openhands_164_patch_contract import ALLOWED


class PinnedSatisfactionTests(unittest.TestCase):
    def test_unpinned_workspace_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "master", str(root)], check=True)
            subprocess.run(
                [
                    "git", "-C", str(root), "-c", "user.name=T", "-c", "user.email=t@e",
                    "commit", "--allow-empty", "-qm", "base",
                ],
                check=True,
            )
            sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
            doc = root / ALLOWED[216]
            doc.parent.mkdir(parents=True)
            doc.write_text(
                "Node 22 Supported Node 24 Supported Node 26 smoke minimum supported\n",
                encoding="utf-8",
            )

            def validator(ws, base):
                if base != sha:
                    raise PermissionError("workspace_base_mismatch")

            out = early_readonly_satisfaction_pinned(
                root, 216, pinned_base_sha="b" * 40, workspace_validator=validator
            )
        self.assertEqual(out["reason"], "satisfaction_workspace_not_pinned_to_master")


if __name__ == "__main__":
    unittest.main()