#!/usr/bin/env python3
"""Fail-closed validator for M4 publication-boundary manifests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOP_LEVEL_KEYS = {"schema", "repository", "target", "sensitive_surfaces", "history", "gates"}
TARGET_KEYS = {"visibility", "mode", "status"}
SURFACE_KEYS = {"path", "disposition", "reason"}
HISTORY_KEYS = {"audit_required", "rewrite_owner_gated"}
GATE_KEYS = {"current_tree_public_safe", "history_public_safe", "exact_head_ci_green", "owner_visibility_approval"}

ALLOWED_VISIBILITY = {"public", "private"}
ALLOWED_MODE = {"canonical-public", "public-code-private-data", "remain-private"}
ALLOWED_STATUS = {"inventory-complete", "extraction-required", "ready-for-owner-gate"}
ALLOWED_DISPOSITION = {"externalize", "sanitize", "syntheticize", "private-runtime", "review"}


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def reject_unknown(obj: dict, allowed: set[str], path: str) -> int | None:
    unknown = sorted(set(obj) - allowed)
    if unknown:
        return fail(f"{path} contains unsupported properties: {', '.join(unknown)}")
    return None


def require_bool(obj: dict, key: str, path: str) -> int | None:
    if type(obj.get(key)) is not bool:
        return fail(f"{path}.{key} must be boolean")
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"cannot read JSON manifest: {exc}")

    if not isinstance(data, dict):
        return fail("manifest root must be an object")
    if result := reject_unknown(data, TOP_LEVEL_KEYS, "manifest"):
        return result

    if type(data.get("schema")) is not int or data["schema"] != 1:
        return fail("schema must equal 1")

    repository = data.get("repository")
    if not isinstance(repository, str) or not repository.strip():
        return fail("repository must be a non-empty string")

    target = data.get("target")
    if not isinstance(target, dict):
        return fail("target object is required")
    if result := reject_unknown(target, TARGET_KEYS, "target"):
        return result

    checks = (
        ("target.visibility", target.get("visibility"), ALLOWED_VISIBILITY),
        ("target.mode", target.get("mode"), ALLOWED_MODE),
        ("target.status", target.get("status"), ALLOWED_STATUS),
    )
    for name, value, allowed in checks:
        if not isinstance(value, str) or value not in allowed:
            return fail(f"{name} has unsupported value {value!r}")

    if target["mode"] in {"canonical-public", "public-code-private-data"} and target["visibility"] != "public":
        return fail("public publication modes require target.visibility public")
    if target["mode"] == "remain-private" and target["visibility"] != "private":
        return fail("remain-private mode requires target.visibility private")

    surfaces = data.get("sensitive_surfaces")
    if not isinstance(surfaces, list):
        return fail("sensitive_surfaces must be an array")
    seen_paths: set[str] = set()
    for index, surface in enumerate(surfaces):
        path = f"sensitive_surfaces[{index}]"
        if not isinstance(surface, dict):
            return fail(f"{path} must be an object")
        if result := reject_unknown(surface, SURFACE_KEYS, path):
            return result
        surface_path = surface.get("path")
        if not isinstance(surface_path, str) or not surface_path.strip():
            return fail(f"{path}.path must be a non-empty string")
        if surface_path in seen_paths:
            return fail(f"duplicate sensitive surface path: {surface_path}")
        seen_paths.add(surface_path)
        disposition = surface.get("disposition")
        if not isinstance(disposition, str) or disposition not in ALLOWED_DISPOSITION:
            return fail(f"{path}.disposition has unsupported value {disposition!r}")
        reason = surface.get("reason")
        if reason is not None and not isinstance(reason, str):
            return fail(f"{path}.reason must be a string when present")

    history = data.get("history")
    if not isinstance(history, dict):
        return fail("history object is required")
    if result := reject_unknown(history, HISTORY_KEYS, "history"):
        return result
    for key in HISTORY_KEYS:
        if result := require_bool(history, key, "history"):
            return result

    gates = data.get("gates")
    if not isinstance(gates, dict):
        return fail("gates object is required")
    if result := reject_unknown(gates, GATE_KEYS, "gates"):
        return result
    for key in GATE_KEYS:
        if result := require_bool(gates, key, "gates"):
            return result

    if target["status"] == "ready-for-owner-gate":
        required = ("current_tree_public_safe", "history_public_safe", "exact_head_ci_green")
        missing = [key for key in required if gates[key] is not True]
        if missing:
            return fail("ready-for-owner-gate requires green technical gates: " + ", ".join(missing))

    if gates["owner_visibility_approval"] and target["status"] != "ready-for-owner-gate":
        return fail("owner visibility approval is only valid at ready-for-owner-gate")

    print("PASS: publication-boundary manifest is structurally valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
