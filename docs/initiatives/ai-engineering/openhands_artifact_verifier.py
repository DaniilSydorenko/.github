#!/usr/bin/env python3
"""Offline, post-run artifact checks for Issue #220. No agent or GitHub writes."""
import argparse
import pathlib
import re
import subprocess
import sys
import tempfile

TARGET = "docs/agent-pilot-proof.md"


def verify(paths, content):
    if sorted(paths) != [TARGET]:
        return "STOP: changed_paths_not_exact"
    if not content or len(content) > 12000:
        return "STOP: missing_or_oversized_proof"
    required = (r"OpenHands", r"(?:Issue\s*#?220|#220)",
                r"distance\s*\(", r"(?:no|not|doesn't|does not)\s+(?:change|modify|alter)")
    if not all(re.search(pattern, content, re.I) for pattern in required):
        return "STOP: proof_content_incomplete"
    return "PASS: offline_artifact_contract_only"


def changed_paths(base):
    """Include tracked, staged and untracked changes; HEAD-only diff is unsafe."""
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise ValueError("base must be an exact 40-character commit SHA")
    subprocess.run(["git", "cat-file", "-e", base + "^{commit}"],
                   check=True, capture_output=True, timeout=15)
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        check=True, capture_output=True, text=True, timeout=15)
    if any(line[:2].strip() in ("D", "R", "C", "U") or
           "D" in line[:2] or "R" in line[:2] or "C" in line[:2]
           for line in result.stdout.splitlines()):
        raise ValueError("deletion, rename or conflict detected")
    diff = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACDMRTUXB", base, "--"],
        check=True, capture_output=True, text=True, timeout=15)
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        check=True, capture_output=True, text=True, timeout=15)
    return sorted(set(diff.stdout.splitlines() + untracked.stdout.splitlines()))



def self_test():
    good = ("OpenHands pilot for Issue #220. Example: distance(a, b). "
            "This does not change library behavior.")
    assert verify([TARGET], good).startswith("PASS:")
    assert verify([TARGET, "package.json"], good) == "STOP: changed_paths_not_exact"
    assert verify([], good) == "STOP: changed_paths_not_exact"
    assert verify([TARGET], "OpenHands Issue #220 distance(a,b)") == "STOP: proof_content_incomplete"
    assert verify([TARGET], good + "x" * 12000) == "STOP: missing_or_oversized_proof"
    with tempfile.TemporaryDirectory() as temp:
        root = pathlib.Path(temp)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit",
                        "--allow-empty", "-qm", "base"], check=True)
        base = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                       text=True).strip()
        original = pathlib.Path.cwd()
        import os
        try:
            os.chdir(root)
            (root / TARGET).parent.mkdir(parents=True)
            (root / TARGET).write_text(good, encoding="utf-8")
            assert changed_paths(base) == [TARGET], "untracked proof not detected"
            (root / "package.json").write_text("{}", encoding="utf-8")
            assert changed_paths(base) == sorted([TARGET, "package.json"])
        finally:
            os.chdir(original)
    print("PASS: artifact verifier detects uncommitted and untracked changes")


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
        content = proof.read_text(encoding="utf-8") if proof.is_file() and not proof.is_symlink() else ""
        verdict = verify(paths, content)
    except (OSError, ValueError, subprocess.SubprocessError, UnicodeError):
        verdict = "STOP: evidence_unavailable"
    print(verdict)
    return 0 if verdict.startswith("PASS:") else 1


if __name__ == "__main__":
    sys.exit(main())
