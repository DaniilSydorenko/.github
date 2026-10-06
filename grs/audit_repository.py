#!/usr/bin/env python3
"""Deterministic repository-surface auditor for GRS v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LEVEL_FAIL = "REQUIRED"
LEVEL_WARN = "RECOMMENDED"

BASE = [
    ("README/status", LEVEL_FAIL, ("README.md", "README")),
    (".gitignore", LEVEL_FAIL, (".gitignore",)),
    ("secret hygiene workflow", LEVEL_FAIL, (".github/workflows/secret-scan.yml",)),
]
LICENSE = ("licensing decision", LEVEL_FAIL, ("LICENSE", "LICENSE.md", "LICENSE.txt"))
PR_TEMPLATE = ("PR template", LEVEL_FAIL, (".github/PULL_REQUEST_TEMPLATE.md", "PULL_REQUEST_TEMPLATE.md"))
ISSUES = ("issue taxonomy", LEVEL_FAIL, (".github/ISSUE_TEMPLATE",))
SECURITY_WARN = ("SECURITY.md", LEVEL_WARN, ("SECURITY.md", ".github/SECURITY.md"))
CONTRIBUTING_WARN = ("CONTRIBUTING.md", LEVEL_WARN, ("CONTRIBUTING.md", ".github/CONTRIBUTING.md"))

CLASS_FILE_CONTROLS = {
    "profile": BASE,
    "oss-library": BASE + [
        LICENSE, PR_TEMPLATE, ISSUES,
        ("SECURITY.md", LEVEL_FAIL, ("SECURITY.md", ".github/SECURITY.md")),
        ("CONTRIBUTING.md", LEVEL_FAIL, ("CONTRIBUTING.md", ".github/CONTRIBUTING.md")),
    ],
    "product": BASE + [LICENSE, PR_TEMPLATE, ISSUES, SECURITY_WARN, CONTRIBUTING_WARN],
    "engineering-labs": BASE + [LICENSE, PR_TEMPLATE, ISSUES, SECURITY_WARN, CONTRIBUTING_WARN],
    "platform": BASE + [LICENSE, PR_TEMPLATE, ISSUES, SECURITY_WARN, CONTRIBUTING_WARN],
    "knowledge": BASE + [
        ("PR template", LEVEL_WARN, (".github/PULL_REQUEST_TEMPLATE.md", "PULL_REQUEST_TEMPLATE.md")),
        ("issue taxonomy", LEVEL_WARN, (".github/ISSUE_TEMPLATE",)),
        CONTRIBUTING_WARN,
    ],
    "historical": [
        ("README/status", LEVEL_FAIL, ("README.md", "README")),
        (".gitignore", LEVEL_WARN, (".gitignore",)),
        ("secret hygiene workflow", LEVEL_FAIL, (".github/workflows/secret-scan.yml",)),
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
        repository = data["repository"]
        repo_class = repository["class"]
        visibility = repository["visibility"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"FAIL: cannot load repository class from manifest: {exc}")
        return 1

    controls = list(CLASS_FILE_CONTROLS.get(repo_class, []))
    if repo_class == "knowledge" and visibility == "public":
        controls.append(LICENSE)

    if not controls:
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
