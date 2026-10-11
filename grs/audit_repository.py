#!/usr/bin/env python3
"""Deterministic repository-surface auditor for GRS v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LEVEL_FAIL = "REQUIRED"
LEVEL_WARN = "RECOMMENDED"
PROFILES_PATH = Path(__file__).resolve().parent / "classes" / "profiles.json"


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def load_profiles(path: Path = PROFILES_PATH) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load repository class profiles: {exc}") from exc

    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("repository class profiles version must equal 1")

    classes = data.get("classes")
    conditional = data.get("conditional")
    if not isinstance(classes, dict) or not isinstance(conditional, list):
        raise ValueError("repository class profiles must define classes and conditional controls")

    for repo_class, controls in classes.items():
        if not isinstance(repo_class, str) or not isinstance(controls, list):
            raise ValueError("repository class profile has invalid shape")
        for control in controls:
            validate_control(control)

    for item in conditional:
        if not isinstance(item, dict):
            raise ValueError("conditional control must be an object")
        if item.get("class") not in classes:
            raise ValueError(f"conditional control references unknown class {item.get('class')!r}")
        when = item.get("when")
        if not isinstance(when, dict) or set(when) != {"visibility"} or when["visibility"] not in {"public", "private"}:
            raise ValueError("conditional control must use a supported visibility condition")
        validate_control(item.get("control"))

    return data


def validate_control(control: object) -> None:
    if not isinstance(control, dict):
        raise ValueError("control must be an object")
    if set(control) != {"name", "level", "candidates"}:
        raise ValueError("control must contain exactly name, level and candidates")
    if not isinstance(control["name"], str) or not control["name"]:
        raise ValueError("control name must be a non-empty string")
    if control["level"] not in {LEVEL_FAIL, LEVEL_WARN}:
        raise ValueError(f"unsupported control level {control['level']!r}")
    candidates = control["candidates"]
    if not isinstance(candidates, list) or not candidates or not all(isinstance(value, str) and value for value in candidates):
        raise ValueError("control candidates must be a non-empty string list")


def candidate_exists(root: Path, candidate: str) -> bool:
    path = root / candidate
    if candidate == ".github/ISSUE_TEMPLATE":
        return path.is_dir()
    return path.is_file()


def exists_any(root: Path, candidates: tuple[str, ...]) -> bool:
    return any(candidate_exists(root, candidate) for candidate in candidates)


def selected_controls(profiles: dict, repo_class: str, visibility: str) -> list[dict]:
    controls = list(profiles["classes"][repo_class])
    for item in profiles["conditional"]:
        if item["class"] == repo_class and item["when"]["visibility"] == visibility:
            controls.append(item["control"])
    return controls


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
        return fail(f"cannot load repository class from manifest: {exc}")

    if type(schema) is not int or schema != 1:
        return fail(f"unsupported manifest schema version {schema!r}")
    if type(standard_version) is not int or standard_version != 1:
        return fail(f"unsupported GRS standard version {standard_version!r}")

    try:
        profiles = load_profiles()
    except ValueError as exc:
        return fail(str(exc))

    if not isinstance(repo_class, str) or repo_class not in profiles["classes"]:
        return fail(f"unsupported repository class {repo_class!r}")
    if not isinstance(visibility, str) or visibility not in {"public", "private"}:
        return fail(f"unsupported repository visibility {visibility!r}")

    failures = 0
    warnings = 0
    for control in selected_controls(profiles, repo_class, visibility):
        name = control["name"]
        level = control["level"]
        candidates = tuple(control["candidates"])
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
