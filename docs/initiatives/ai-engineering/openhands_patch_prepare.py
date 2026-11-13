#!/usr/bin/env python3
"""Create a reviewable, single-file Issue #220 patch after verifier approval.

Never pushes, commits, opens PRs or invokes an LLM.
"""
import argparse
import pathlib
import subprocess
import sys
import tempfile

from openhands_artifact_verifier import TARGET, changed_paths, verify


def prepare(workspace, base, output):
    root = pathlib.Path(workspace).resolve(strict=True)
    destination = pathlib.Path(output).resolve()
    if not (root / ".git").exists():
        raise ValueError("not a Git checkout")
    if destination == root or root in destination.parents:
        raise ValueError("patch output must be outside target checkout")
    if changed_paths_in(root, base) != [TARGET]:
        raise ValueError("unexpected changed paths")
    target = root / TARGET
    if target.is_symlink() or not target.is_file():
        raise ValueError("proof is not a regular file")
    content = target.read_text(encoding="utf-8")
    if not verify([TARGET], content).startswith("PASS:"):
        raise ValueError("proof contract failed")
    # Diff --no-index captures a new, untracked file without staging or committing.
    with tempfile.TemporaryDirectory() as temp:
        empty = pathlib.Path(temp) / "empty"
        empty.write_bytes(b"")
        result = subprocess.run(["git", "diff", "--no-index", "--", str(empty), str(target)],
                                capture_output=True, timeout=15)
        if result.returncode != 1 or not result.stdout:
            raise ValueError("cannot construct patch")
        patch = result.stdout.replace(str(empty).encode(), ("a/" + TARGET).encode()).replace(
            str(target).encode(), ("b/" + TARGET).encode())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(patch)
    return destination


def changed_paths_in(root, base):
    original = pathlib.Path.cwd()
    import os
    try:
        os.chdir(root)
        return changed_paths(base)
    finally:
        os.chdir(original)


def self_test():
    with tempfile.TemporaryDirectory() as temp:
        root = pathlib.Path(temp) / "repo"
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit",
                        "--allow-empty", "-qm", "base"], check=True)
        base = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                       text=True).strip()
        proof = root / TARGET
        proof.parent.mkdir(parents=True)
        proof.write_text("OpenHands Issue #220: distance(a,b). This does not change behavior.\n")
        patch = pathlib.Path(temp) / "proof.patch"
        prepare(root, base, patch)
        assert b"docs/agent-pilot-proof.md" in patch.read_bytes()
        subprocess.run(["git", "-C", str(root), "apply", "--check", str(patch)], check=True)
        (root / "package.json").write_text("{}", encoding="utf-8")
        try:
            prepare(root, base, patch)
        except ValueError as error:
            assert str(error) == "unexpected changed paths"
        else:
            raise AssertionError("extra file accepted")
    print("PASS: isolated patch preparation and extra-file rejection")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--workspace")
    parser.add_argument("--base-sha")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.self_test and not any((args.workspace, args.base_sha, args.output)):
        self_test()
        return 0
    if args.self_test or not all((args.workspace, args.base_sha, args.output)):
        parser.error("use --self-test or --workspace PATH --base-sha SHA --output FILE")
    try:
        print(prepare(args.workspace, args.base_sha, args.output))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError, UnicodeError) as error:
        print("STOP: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
