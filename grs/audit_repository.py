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

def candidate_exists(root: Path, candidate: str) -> bool:
    path = root / candidate
    # GRS controls distinguish required files from required directories.
    # A directory named README.md/ must never satisfy a README requirement,
    # and a plain file named .github/ISSUE_TEMPLATE must never satisfy the
    # issue-template directory requirement.
    if candidate == ".github/ISSUE_TEMPLATE":
        return path.is_dir()
    return path.is_file()

def exists_any(root: Path, candidates: tuple[str, ...]) -> bool:
    return any(candidate_exists(root, candidate) for candidate in candidates)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        schema = data["schema"]
        standard_version = data["standard"]["version"]
        repository = data["repository"]
        repo_class = repository["class"]
        visibility = repository["visibility"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"FAIL: cannot load repository class from manifest: {exc}")
        return 1

    # The auditor must independently reject unsupported manifest contracts.
    # A passing file-surface audit is not valid for an unknown GRS version.
    if type(schema) is not int or schema != 1:
        print(f"FAIL: unsupported manifest schema version {schema!r}")
        return 1
    if type(standard_version) is not int or standard_version != 1:
        print(f"FAIL: unsupported GRS standard version {standard_version!r}")
        return 1

    # Reject unsupported values before selecting controls. Unknown classes must
    # never be treated as an audit PASS, even when no files are present.
    if not isinstance(repo_class, str) or repo_class not in CLASS_FILE_CONTROLS:
        print(f"FAIL: unsupported repository class {repo_class!r}")
        return 1
    if not isinstance(visibility, str) or visibility not in {"public", "private"}:
        print(f"FAIL: unsupported repository visibility {visibility!r}")
        return 1

    controls = list(CLASS_FILE_CONTROLS[repo_class])
    if repo_class == "knowledge" and visibility == "public":
        controls.append(LICENSE)

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
