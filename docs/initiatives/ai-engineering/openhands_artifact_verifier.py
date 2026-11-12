#!/usr/bin/env python3
"""Offline, post-run artifact checks for Issue #220. No agent or GitHub writes."""
import argparse
import pathlib
import re
import subprocess
import sys

TARGET = "docs/agent-pilot-proof.md"


def verify(paths, content):
    if paths != [TARGET]:
        return "STOP: changed_paths_not_exact"
    if not content or len(content) > 12000:
        return "STOP: missing_or_oversized_proof"
    required = (r"OpenHands", r"(?:Issue\s*#?220|#220)",
                r"distance\s*\(", r"(?:no|not|doesn't|does not)\s+(?:change|modify|alter)")
    if not all(re.search(pattern, content, re.I) for pattern in required):
        return "STOP: proof_content_incomplete"
    return "PASS: offline_artifact_contract_only"


def changed_paths(base):
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise ValueError("base must be an exact 40-character commit SHA")
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACDMRTUXB", base, "HEAD"],
        check=True, capture_output=True, text=True, timeout=15)
    return [p for p in result.stdout.splitlines() if p]


def self_test():
    good = ("OpenHands pilot for Issue #220. Example: distance(a, b). "
            "This does not change library behavior.")
    assert verify([TARGET], good).startswith("PASS:")
    assert verify([TARGET, "package.json"], good) == "STOP: changed_paths_not_exact"
    assert verify([], good) == "STOP: changed_paths_not_exact"
    assert verify([TARGET], "OpenHands Issue #220 distance(a,b)") == "STOP: proof_content_incomplete"
    assert verify([TARGET], good + "x" * 12000) == "STOP: missing_or_oversized_proof"
    print("PASS: offline artifact verifier fixtures (no agent execution)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--base-sha")
    args = parser.parse_args()
    if args.self_test and not args.base_sha:
        self_test()
        return 0
    if not args.base_sha or args.self_test:
        parser.error("provide exactly --self-test or --base-sha")
    try:
        paths = changed_paths(args.base_sha)
        proof = pathlib.Path(TARGET)
        content = proof.read_text(encoding="utf-8") if proof.is_file() else ""
        verdict = verify(paths, content)
    except (OSError, ValueError, subprocess.SubprocessError, UnicodeError):
        verdict = "STOP: evidence_unavailable"
    print(verdict)
    return 0 if verdict.startswith("PASS:") else 1


if __name__ == "__main__":
    sys.exit(main())
