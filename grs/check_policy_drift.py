#!/usr/bin/env python3
"""Detect deterministic drift across GRS class-policy sources."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_SCHEMA = ROOT / "repository.schema.json"
DEFAULT_PROFILES = ROOT / "classes" / "profiles.json"
DEFAULT_VALIDATOR = ROOT / "validator.py"
DEFAULT_PILOTS = ROOT / "pilots"


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON {path}: {exc}") from exc


def schema_classes(path: Path) -> set[str]:
    data = load_json(path)
    try:
        values = data["properties"]["repository"]["properties"]["class"]["enum"]
    except (KeyError, TypeError) as exc:
        raise ValueError("repository schema does not expose repository.class enum") from exc
    if not isinstance(values, list) or not values or not all(isinstance(value, str) for value in values):
        raise ValueError("repository.class enum must be a non-empty string list")
    return set(values)


def profile_classes(path: Path) -> set[str]:
    data = load_json(path)
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("class profiles version must equal 1")
    classes = data.get("classes")
    if not isinstance(classes, dict):
        raise ValueError("class profiles must define classes")
    return set(classes)


def validator_classes(path: Path) -> set[str]:
    spec = importlib.util.spec_from_file_location("grs_validator_for_drift", path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load validator module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    values = getattr(module, "ALLOWED_CLASSES", None)
    if not isinstance(values, set) or not values or not all(isinstance(value, str) for value in values):
        raise ValueError("validator ALLOWED_CLASSES must be a non-empty string set")
    return set(values)


def pilot_classes(directory: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(directory.glob("*.repository.json")):
        data = load_json(path)
        try:
            value = data["repository"]["class"]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"{path.name} does not expose repository.class") from exc
        if not isinstance(value, str):
            raise ValueError(f"{path.name} repository.class must be a string")
        result[path.name] = value
    return result


def compare(label: str, expected: set[str], actual: set[str]) -> list[str]:
    messages: list[str] = []
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        messages.append(f"{label} missing classes: {', '.join(missing)}")
    if extra:
        messages.append(f"{label} has extra classes: {', '.join(extra)}")
    return messages


def run(schema: Path, profiles: Path, validator: Path, pilots: Path) -> int:
    try:
        schema_set = schema_classes(schema)
        profile_set = profile_classes(profiles)
        validator_set = validator_classes(validator)
        pilots_map = pilot_classes(pilots)
    except ValueError as exc:
        return fail(str(exc))

    errors: list[str] = []
    errors.extend(compare("class profiles", schema_set, profile_set))
    errors.extend(compare("validator", schema_set, validator_set))

    unknown_pilots = {
        filename: repo_class
        for filename, repo_class in pilots_map.items()
        if repo_class not in schema_set
    }
    for filename, repo_class in sorted(unknown_pilots.items()):
        errors.append(f"pilot {filename} uses unknown class {repo_class!r}")

    if errors:
        for message in errors:
            print(f"FAIL: {message}")
        return 1

    print("PASS: GRS class taxonomy is synchronized across schema, validator and class profiles")
    print(f"PASS: {len(pilots_map)} pilot manifests use known repository classes")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--validator", type=Path, default=DEFAULT_VALIDATOR)
    parser.add_argument("--pilots", type=Path, default=DEFAULT_PILOTS)
    args = parser.parse_args()
    return run(args.schema, args.profiles, args.validator, args.pilots)


if __name__ == "__main__":
    sys.exit(main())
