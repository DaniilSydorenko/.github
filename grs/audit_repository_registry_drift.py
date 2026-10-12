#!/usr/bin/env python3
"""Read-only live drift audit for the Engineering Governance v1 repository registry.

This tool deliberately does not mutate repositories and is not a required CI gate.
It compares the canonical discovery registry with live GitHub repository metadata
and declared discovery paths. A token with read access to all seven repositories
is required for an authoritative audit.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True)
class Finding:
    kind: str
    repository: str
    detail: str


def discovery_paths(record: dict) -> list[str]:
    discovery = record.get("discovery") or {}
    paths: list[str] = []

    for key in ("roadmap", "agent", "authority", "governance"):
        value = discovery.get(key)
        if isinstance(value, str) and value:
            paths.append(value)

    for tracker in discovery.get("specialized_trackers") or []:
        if isinstance(tracker, dict):
            value = tracker.get("path")
            if isinstance(value, str) and value:
                paths.append(value)

    # Preserve declaration order while removing accidental duplicates.
    return list(dict.fromkeys(paths))


def audit_registry(
    data: dict,
    api_get: Callable[[str], tuple[int, dict | list | None]],
) -> list[Finding]:
    findings: list[Finding] = []

    for record in data.get("repositories") or []:
        repository = record.get("repository")
        declared_branch = record.get("default_branch")

        if not isinstance(repository, str) or not repository:
            findings.append(Finding("operational", "<unknown>", "invalid repository record"))
            continue

        status, repo_data = api_get(f"/repos/{repository}")
        if status == 404:
            findings.append(
                Finding(
                    "operational",
                    repository,
                    "repository is not readable with the supplied credentials",
                )
            )
            continue
        if status != 200 or not isinstance(repo_data, dict):
            findings.append(
                Finding(
                    "operational",
                    repository,
                    f"repository metadata lookup failed with HTTP {status}",
                )
            )
            continue

        live_branch = repo_data.get("default_branch")
        if live_branch != declared_branch:
            findings.append(
                Finding(
                    "drift",
                    repository,
                    f"default branch drift: registry={declared_branch!r}, live={live_branch!r}",
                )
            )
            # Pointer checks still use the declared branch so the report explains
            # whether the registry's declared discovery contract remains resolvable.

        if not isinstance(declared_branch, str) or not declared_branch:
            findings.append(Finding("operational", repository, "declared default branch is invalid"))
            continue

        encoded_ref = urllib.parse.quote(declared_branch, safe="")
        for path in discovery_paths(record):
            encoded_path = urllib.parse.quote(path, safe="/")
            status, _ = api_get(
                f"/repos/{repository}/contents/{encoded_path}?ref={encoded_ref}"
            )
            if status == 404:
                findings.append(
                    Finding(
                        "drift",
                        repository,
                        f"declared discovery path is missing on {declared_branch}: {path}",
                    )
                )
            elif status != 200:
                findings.append(
                    Finding(
                        "operational",
                        repository,
                        f"path lookup failed with HTTP {status}: {path}",
                    )
                )

    return findings


def make_api_get(api_url: str, token: str) -> Callable[[str], tuple[int, dict | list | None]]:
    base = api_url.rstrip("/")

    def api_get(path: str) -> tuple[int, dict | list | None]:
        request = urllib.request.Request(
            f"{base}{path}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "engineering-governance-v1-drift-audit",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = response.read().decode("utf-8")
                return response.status, json.loads(payload) if payload else None
        except urllib.error.HTTPError as exc:
            try:
                payload = exc.read().decode("utf-8")
                body = json.loads(payload) if payload else None
            except (UnicodeDecodeError, json.JSONDecodeError):
                body = None
            return exc.code, body

    return api_get


def print_findings(findings: Iterable[Finding]) -> None:
    for finding in findings:
        label = "DRIFT" if finding.kind == "drift" else "ERROR"
        print(f"{label}: {finding.repository}: {finding.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit repository discovery pointers against live GitHub state."
    )
    parser.add_argument(
        "registry",
        nargs="?",
        default="governance/repository-registry.json",
        help="path to the canonical repository registry",
    )
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print(
            "ERROR: GITHUB_TOKEN with read access to all governed repositories is required; "
            "refusing a partial/anonymous audit."
        )
        return 1

    try:
        data = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read registry: {exc}")
        return 1

    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    findings = audit_registry(data, make_api_get(api_url, token))
    print_findings(findings)

    if any(item.kind == "operational" for item in findings):
        print("ERROR: audit incomplete; operational/access failures must not be reported as clean")
        return 1
    if any(item.kind == "drift" for item in findings):
        print("DRIFT: repository discovery registry no longer matches live GitHub state")
        return 2

    print("PASS: all seven repository branches and declared discovery pointers match live GitHub state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
