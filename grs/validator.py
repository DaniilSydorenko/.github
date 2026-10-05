#!/usr/bin/env python3
"""Deterministic GitHub Repository Standard (GRS) v1 manifest validator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ALLOWED_CLASSES = {
    "profile", "oss-library", "product", "engineering-labs",
    "knowledge", "platform", "historical",
}
ALLOWED_MATURITY = {"experimental", "active", "maintained", "stable", "frozen", "archived"}
ALLOWED_VISIBILITY = {"public", "private"}


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"cannot read JSON manifest: {exc}")

    if data.get("schema") != 1:
        return fail("schema must equal 1")
    if data.get("standard", {}).get("version") != 1:
        return fail("standard.version must equal 1")

    repository = data.get("repository")
    portfolio = data.get("portfolio")
    if not isinstance(repository, dict) or not isinstance(portfolio, dict):
        return fail("repository and portfolio objects are required")

    checks = (
        ("repository.class", repository.get("class"), ALLOWED_CLASSES),
        ("repository.maturity", repository.get("maturity"), ALLOWED_MATURITY),
        ("repository.visibility", repository.get("visibility"), ALLOWED_VISIBILITY),
    )
    for name, value, allowed in checks:
        if value not in allowed:
            return fail(f"{name} has unsupported value {value!r}")

    for key in ("flagship", "pin_candidate"):
        if not isinstance(portfolio.get(key), bool):
            return fail(f"portfolio.{key} must be boolean")

    print("PASS: GRS v1 manifest is structurally valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
