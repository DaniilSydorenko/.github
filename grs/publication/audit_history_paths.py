#!/usr/bin/env python3
"""Read-only Git-history audit for publication-boundary sensitive paths.

This tool never rewrites history. It answers whether any path declared in a
publication manifest has existed anywhere in the repository's reachable Git
history. A match (including a supposedly private-runtime-only path) requires review before a private→public
visibility change.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

AUDITED_DISPOSITIONS = {"externalize", "sanitize", "syntheticize", "private-runtime", "review"}


def fail(message: str, code: int = 1) -> int:
    print(f"FAIL: {message}")
    return code


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def normalize(path: str) -> str:
    """Remove only literal ./ prefixes; preserve hidden-directory dots (.local)."""
    value = path.strip()
    while value.startswith("./"):
        value = value[2:]
    return value


def matches(candidate: str, sensitive: str) -> bool:
    candidate = normalize(candidate)
    sensitive = normalize(sensitive)
    if not candidate or not sensitive:
        return False
    if sensitive.endswith("/"):
        return candidate.startswith(sensitive)
    return candidate == sensitive or candidate.startswith(sensitive + "/")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    repo = args.repository.resolve()
    manifest_path = args.manifest.resolve()

    if not (repo / ".git").exists():
        return fail(f"not a Git working tree: {repo}")

    shallow = git(repo, "rev-parse", "--is-shallow-repository")
    if shallow.returncode != 0:
        return fail(f"cannot determine repository history completeness: {shallow.stderr.strip()}")
    if shallow.stdout.strip().lower() == "true":
        return fail(
            "repository is shallow; refusing to report publication history clean from incomplete history"
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"cannot read manifest: {exc}")

    if not isinstance(manifest, dict):
        return fail("publication manifest root must be an object")
    history = manifest.get("history")
    if not isinstance(history, dict):
        return fail("manifest history must be an object")
    if history.get("audit_required") is not True:
        return fail("history.audit_required must be true (not false, missing, or malformed)")

    surfaces = manifest.get("sensitive_surfaces")
    if not isinstance(surfaces, list):
        return fail("manifest sensitive_surfaces must be an array")

    sensitive_paths_set: set[str] = set()
    for index, surface in enumerate(surfaces):
        if not isinstance(surface, dict) or surface.get("disposition") not in AUDITED_DISPOSITIONS:
            return fail(f"sensitive_surfaces[{index}]: missing or unsupported disposition")
        raw_path = surface.get("path")
        if not isinstance(raw_path, str):
            return fail(f"sensitive_surfaces[{index}]: path must be a string")
        sensitive = normalize(raw_path)
        parts = sensitive.split("/")
        if (
            not sensitive
            or sensitive.startswith("/")
            or "\\" in sensitive
            or "//" in sensitive
            or any(part in {".", ".."} for part in parts)
        ):
            return fail(f"sensitive_surfaces[{index}]: unsafe or ambiguous Git path")
        sensitive_paths_set.add(sensitive)
    sensitive_paths = sorted(sensitive_paths_set)

    if not sensitive_paths:
        print("PASS: no history-audited sensitive paths are declared")
        return 0

    result = git(repo, "log", "--all", "--name-only", "-z", "--pretty=format:")
    if result.returncode != 0:
        return fail(f"git log failed: {result.stderr.strip()}")

    # NUL-delimited output avoids Git's C-quoted filenames (tabs/newlines/non-ASCII).
    historical_paths = {normalize(path) for path in result.stdout.split("\0") if path}
    findings: dict[str, list[str]] = {}

    for sensitive in sensitive_paths:
        matched = sorted(path for path in historical_paths if matches(path, sensitive))
        if matched:
            findings[sensitive] = matched

    if findings:
        print("REVIEW_REQUIRED: sensitive publication surfaces exist in reachable Git history")
        for sensitive, matched in findings.items():
            print(f"HISTORY_MATCH: {sensitive}")
            for path in matched[:20]:
                print(f"  - {path}")
            if len(matched) > 20:
                print(f"  - ... {len(matched) - 20} more")
        print("No history mutation was performed.")
        return 2

    print("PASS: declared sensitive publication surfaces are absent from reachable Git history")
    return 0


if __name__ == "__main__":
    sys.exit(main())
