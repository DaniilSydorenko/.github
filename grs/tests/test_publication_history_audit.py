#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDITOR = ROOT / "grs" / "publication" / "audit_history_paths.py"


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True)


class HistoryPathAuditTests(unittest.TestCase):
    def make_repo(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = Path(tmp.name)
        self.assertEqual(run("git", "init", "-q", cwd=repo).returncode, 0)
        self.assertEqual(run("git", "config", "user.email", "test@example.com", cwd=repo).returncode, 0)
        self.assertEqual(run("git", "config", "user.name", "Test", cwd=repo).returncode, 0)
        return repo

    def commit_file(self, repo: Path, path: str, content: str) -> None:
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self.assertEqual(run("git", "add", path, cwd=repo).returncode, 0)
        result = run("git", "commit", "-q", "-m", f"add {path}", cwd=repo)
        self.assertEqual(result.returncode, 0, result.stderr)

    def write_manifest(self, repo: Path, surfaces: list[dict]) -> Path:
        path = repo / "manifest.json"
        path.write_text(json.dumps({"sensitive_surfaces": surfaces}), encoding="utf-8")
        return path

    def audit(self, repo: Path, manifest: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(AUDITOR), str(repo), str(manifest)],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_passes_when_sensitive_path_never_existed(self) -> None:
        repo = self.make_repo()
        self.commit_file(repo, "src/index.ts", "export {}")
        manifest = self.write_manifest(
            repo, [{"path": "private/", "disposition": "externalize"}]
        )
        result = self.audit(repo, manifest)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS:", result.stdout)

    def test_refuses_shallow_repository(self) -> None:
        source = self.make_repo()
        self.commit_file(source, "private/old.txt", "secret")
        self.commit_file(source, "src/index.ts", "export {}")

        clone_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(clone_tmp.cleanup)
        clone = Path(clone_tmp.name) / "clone"
        result = run(
            "git",
            "clone",
            "-q",
            "--depth",
            "1",
            f"file://{source}",
            str(clone),
            cwd=source.parent,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        manifest = self.write_manifest(
            clone, [{"path": "private/", "disposition": "externalize"}]
        )
        result = self.audit(clone, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("repository is shallow", result.stdout)
        self.assertNotIn("PASS:", result.stdout)

    def test_detects_deleted_sensitive_path_in_history(self) -> None:
        repo = self.make_repo()
        self.commit_file(repo, "daniil/gap-map.md", "private")
        self.assertEqual(run("git", "rm", "daniil/gap-map.md", cwd=repo).returncode, 0)
        self.assertEqual(run("git", "commit", "-q", "-m", "remove private path", cwd=repo).returncode, 0)
        manifest = self.write_manifest(
            repo, [{"path": "daniil/", "disposition": "externalize"}]
        )
        result = self.audit(repo, manifest)
        self.assertEqual(result.returncode, 2)
        self.assertIn("HISTORY_MATCH: daniil/", result.stdout)
        self.assertIn("daniil/gap-map.md", result.stdout)

    def test_private_runtime_in_history_blocks_publication(self) -> None:
        repo = self.make_repo()
        self.commit_file(repo, ".local/migration/example.txt", "local")
        manifest = self.write_manifest(
            repo, [{"path": ".local/migration/", "disposition": "private-runtime"}]
        )
        result = self.audit(repo, manifest)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("HISTORY_MATCH: .local/migration/", result.stdout)
        self.assertIn(".local/migration/example.txt", result.stdout)

    def test_uncommitted_private_runtime_path_is_history_clean(self) -> None:
        repo = self.make_repo()
        self.commit_file(repo, "src/index.ts", "export {}")
        manifest = self.write_manifest(
            repo, [{"path": ".local/migration/", "disposition": "private-runtime"}]
        )
        result = self.audit(repo, manifest)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hidden_directory_does_not_alias_public_directory(self) -> None:
        repo = self.make_repo()
        self.commit_file(repo, "local/migration/example.txt", "public")
        manifest = self.write_manifest(
            repo, [{"path": ".local/migration/", "disposition": "private-runtime"}]
        )
        result = self.audit(repo, manifest)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_explicit_relative_prefix_preserves_hidden_path(self) -> None:
        repo = self.make_repo()
        self.commit_file(repo, ".local/migration/example.txt", "private")
        manifest = self.write_manifest(
            repo, [{"path": "./.local/migration/", "disposition": "private-runtime"}]
        )
        result = self.audit(repo, manifest)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("HISTORY_MATCH: .local/migration/", result.stdout)

    def test_path_traversal_cannot_silently_pass_history(self) -> None:
        repo = self.make_repo()
        self.commit_file(repo, "src/index.ts", "export {}")
        manifest = self.write_manifest(
            repo, [{"path": "../private/", "disposition": "externalize"}]
        )
        result = self.audit(repo, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("unsafe or ambiguous Git path", result.stdout)

    def test_unsupported_disposition_cannot_skip_audit(self) -> None:
        repo = self.make_repo()
        self.commit_file(repo, "src/index.ts", "export {}")
        manifest = self.write_manifest(
            repo, [{"path": "private/", "disposition": "untracked"}]
        )
        result = self.audit(repo, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("unsupported disposition", result.stdout)

    def test_exact_file_surface_matches_history(self) -> None:
        repo = self.make_repo()
        self.commit_file(repo, "docs/PUBLIC_ACTIVATION.md", "internal keys")
        manifest = self.write_manifest(
            repo, [{"path": "docs/PUBLIC_ACTIVATION.md", "disposition": "sanitize"}]
        )
        result = self.audit(repo, manifest)
        self.assertEqual(result.returncode, 2)
        self.assertIn("HISTORY_MATCH: docs/PUBLIC_ACTIVATION.md", result.stdout)


if __name__ == "__main__":
    unittest.main()
