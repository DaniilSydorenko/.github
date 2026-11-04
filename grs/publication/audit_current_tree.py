#!/usr/bin/env python3
"""Read-only M4 GitHub-tree snapshot audit; no publication authorization.

Consumes an independently fetched GitHub REST git/trees/<ref>?recursive=1
JSON response. Never assumes that a path absence proves Git history safe.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from audit_history_paths import AUDITED_DISPOSITIONS, matches, normalize


def audit(tree: object, manifest: object) -> tuple[int, dict]:
    if not isinstance(tree, dict) or tree.get("truncated") is not False:
        return 1, {"status": "INVALID", "reason": "Git tree missing or truncated"}
    if not isinstance(tree.get("sha"), str) or re.fullmatch(r"[0-9a-f]{40}", tree["sha"]) is None:
        return 1, {"status": "INVALID", "reason": "Git tree SHA missing or invalid"}
    entries = tree.get("tree")
    if not isinstance(entries, list):
        return 1, {"status": "INVALID", "reason": "Git tree entries missing"}
    if not isinstance(manifest, dict):
        return 1, {"status": "INVALID", "reason": "publication manifest must be object"}
    surfaces = manifest.get("sensitive_surfaces")
    if not isinstance(surfaces, list):
        return 1, {"status": "INVALID", "reason": "sensitive_surfaces must be list"}
    paths: set[str] = set()
    entry_paths: set[str] = set()
    for i, item in enumerate(entries):
        if (not isinstance(item, dict) or not isinstance(item.get("path"), str)
                or item.get("type") not in {"blob", "tree", "commit"}
                or not isinstance(item.get("sha"), str)
                or re.fullmatch(r"[0-9a-f]{40}", item["sha"]) is None):
            return 1, {"status": "INVALID", "reason": f"invalid Git tree entry {i}"}
        entry_path = item["path"]
        # A malformed or duplicated snapshot must never produce a false clean report.
        if (not entry_path or entry_path.startswith("/") or "\\" in entry_path
                or "//" in entry_path or entry_path in entry_paths
                or any(part in {"", ".", ".."} for part in entry_path.split("/"))):
            return 1, {"status": "INVALID", "reason": f"unsafe/duplicate Git tree entry {i}"}
        entry_paths.add(entry_path)
        if item["type"] == "blob":
            paths.add(entry_path)
    if not paths:
        return 1, {"status": "UNKNOWN", "reason": "no source blobs found; insufficient tree evidence"}
    seen: set[str] = set()
    findings: list[dict] = []
    matched_blobs: set[str] = set()
    for i, surface in enumerate(surfaces):
        if not isinstance(surface, dict) or surface.get("disposition") not in AUDITED_DISPOSITIONS:
            return 1, {"status": "INVALID", "reason": f"invalid sensitive surface {i}"}
        raw_path = surface.get("path")
        if not isinstance(raw_path, str):
            return 1, {"status": "INVALID", "reason": f"invalid path in surface {i}"}
        path = normalize(raw_path)
        if (not path or path.startswith("/") or "\\" in path or "//" in path
                or any(part in {".", ".."} for part in path.split("/")) or path in seen):
            return 1, {"status": "INVALID", "reason": f"unsafe/duplicate path in surface {i}"}
        seen.add(path)
        matching = sorted(p for p in paths if matches(p, path))
        matched_blobs.update(matching)
        findings.append({
            "path": path,
            "disposition": surface["disposition"],
            "tracked_count": len(matching),
            "current_tree_review_required": bool(matching),
        })
    flagged = len(matched_blobs)
    report = {
        "status": "REVIEW_REQUIRED" if flagged else "NO_DECLARED_CURRENT_TREE_PATH_MATCH",
        "tree_sha": tree["sha"],
        "repository": manifest.get("repository"),
        "tree_truncated": False,
        "blobs_scanned": len(paths),
        "matching_blobs": flagged,
        "surfaces": findings,
        "history_audited": False,
        "contents_audited": False,
        "publication_authorized": False,
    }
    return (2 if flagged else 0), report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tree_snapshot", type=Path)
    parser.add_argument("publication_manifest", type=Path)
    args = parser.parse_args()
    try:
        tree = json.loads(args.tree_snapshot.read_text(encoding="utf-8"))
        manifest = json.loads(args.publication_manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "INVALID", "reason": str(exc)}))
        return 1
    code, result = audit(tree, manifest)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
