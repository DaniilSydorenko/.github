#!/usr/bin/env python3
"""Read-only GRS fleet evidence reporter; no enforcement or GitHub writes.

Reads existing governance/repository-registry.json and optionally an offline
JSON evidence snapshot. Missing evidence is UNKNOWN, never compliant.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


DIMENSIONS = ("discovery", "manifest", "class_profile", "ci", "operational")
STATES = {"PASS", "FAIL", "UNKNOWN", "EXCEPTION"}


def build_report(registry: dict, evidence: dict) -> dict:
    records = registry.get("repositories", [])
    if not isinstance(records, list):
        raise ValueError("registry.repositories must be a list")
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be an object")
    expected = {record["repository"] for record in records}
    extra = set(evidence) - expected
    if extra:
        raise ValueError(f"unregistered evidence repositories: {sorted(extra)}")
    rows = []
    for record in records:
        name = record["repository"]
        supplied = evidence.get(name, {})
        if not isinstance(supplied, dict):
            raise ValueError(f"{name}: evidence must be an object")
        if set(supplied) - set(DIMENSIONS):
            raise ValueError(f"{name}: unsupported evidence dimensions")
        result = {}
        for dimension in DIMENSIONS:
            item = supplied.get(dimension, {})
            if not isinstance(item, dict):
                raise ValueError(f"{name}/{dimension}: evidence must be an object")
            state = item.get("state", "UNKNOWN")
            if state not in STATES:
                raise ValueError(f"{name}/{dimension}: invalid state")
            source = item.get("source")
            if state != "UNKNOWN" and (not isinstance(source, str) or not source.strip()):
                raise ValueError(f"{name}/{dimension}: {state} requires evidence source")
            if state == "EXCEPTION" and not item.get("owner_approval"):
                raise ValueError(f"{name}/{dimension}: exception requires owner approval")
            result[dimension] = {"state": state, "source": source or None}
            if state == "EXCEPTION":
                result[dimension]["owner_approval"] = item["owner_approval"]
        rows.append({"repository": name, "grs_class": record["grs_class"], "dimensions": result})
    return {
        "schema_version": 1,
        "policy": "read-only; UNKNOWN is not PASS; no inferred CI or runtime enforcement",
        "repository_count": len(rows),
        "rows": rows,
        "counts": {dimension: {state: sum(
            row["dimensions"][dimension]["state"] == state for row in rows
        ) for state in sorted(STATES)} for dimension in DIMENSIONS},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=Path("governance/repository-registry.json"))
    parser.add_argument("--evidence", type=Path, help="Optional reviewed JSON keyed by repository")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    evidence = json.loads(args.evidence.read_text(encoding="utf-8")) if args.evidence else {}
    report = build_report(registry, evidence)
    result = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
