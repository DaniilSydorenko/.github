#!/usr/bin/env python3
"""Deterministic repository-surface auditor for GRS v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LEVEL_FAIL = "REQUIRED"
LEVEL_WARN = "RECOMMENDED"

CLASS_FILE_CONTROLS = {
    "profile": [
        ("README/status", LEVEL_FAIL, ("README.md", "README")),
        (".gitignore", LEVEL_FAIL, (".gitignore",)),
        ("secret hygiene workflow", LEVEL_FAIL, (".github/workflows/secret-scan.yml",)),
    ],
    "oss-library": [
        ("README/status", LEVEL_FAIL, ("README.md", "README")),
        (".gitignore", LEVEL_FAIL, (".gitignore",)),
        ("licensing decision", LEVEL_FAIL, ("LICENSE", "LICENSE.md", "LICENSE.txt")),
        ("secret hygiene workflow", LEVEL_FAIL, (".github/workflows/secret-scan.yml",)),
        ("PR template", LEVEL_FAIL, (".github/PULL_REQUEST_TEMPLATE.md", "PULL_REQUEST_TEMPLATE.md")),
        ("issue taxonomy", LEVEL_FAIL, (".github/ISSUE_TEMPLATE",)),
        ("SECURITY.md", LEVEL_FAIL, ("SECURITY.md", ".github/SECURITY.md")),
        ("CONTRIBUTING.md", LEVEL_FAIL, ("CONTRIBUTING.md", ".github/CONTRIBUTING.md")),
    ],
}

def exists_any(root: Path, candidates: tuple[str, ...]) -> bool:
    return any((root / candidate).exists() for candidate in candidates)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        repo_class = data["repository"]["class"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"FAIL: cannot load repository class from manifest: {exc}")
        return 1

    controls = CLASS_FILE_CONTROLS.get(repo_class)
    if controls is None:
        print(f"PASS: no deterministic file-surface controls implemented yet for class {repo_class!r}")
        return 0

    failures = 0
    warnings = 0
    for name, level, candidates in controls:
        if exists_any(args.root, candidates):
            print(f"PASS: {name}")
        elif level == LEVEL_FAIL:
            failures += 1
            print(f"FAIL: {name} — expected one of: {', '.join(candidates)}")
        else:
            warnings += 1
            print(f"WARN: {name} — expected one of: {', '.join(candidates)}")

    print(f"SUMMARY: {failures} FAIL, {warnings} WARN")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())
