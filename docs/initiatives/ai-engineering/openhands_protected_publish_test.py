#!/usr/bin/env python3
"""Offline provenance and replay tests: no network, credentials or GitHub writes."""
import pathlib
import subprocess
import tempfile

from openhands_protected_publish import verify_run, validate_patch, CONTROL, WORKFLOW
from openhands_patch_prepare import prepare
from openhands_draft_handoff import TARGET


def reject(fn):
    try:
        fn()
    except (ValueError, subprocess.CalledProcessError):
        return
    raise AssertionError("unsafe input accepted")


def main():
    sha = "a" * 40
    run = dict(id=123, repository={"full_name": CONTROL}, path=WORKFLOW,
               event="workflow_dispatch", head_branch="main",
               actor={"login": "DaniilSydorenko"}, conclusion="success",
               run_attempt=1, head_sha=sha)
    jobs = [{"name": "manual-pilot-live-execute", "conclusion": "success"}]
    assert verify_run(run, jobs, expected_run_id=123, current_control_sha=sha)
    for field, value in (
        ("event", "pull_request"), ("head_branch", "feature"),
        ("path", "other.yml"), ("conclusion", "failure"),
        ("run_attempt", 2), ("head_sha", "b" * 40),
        ("actor", {"login": "attacker"}), ("repository", {"full_name": "other/repo"})
    ):
        reject(lambda field=field, value=value:
               verify_run({**run, field: value}, jobs,
                          expected_run_id=123, current_control_sha=sha))
    reject(lambda: verify_run(run, jobs, expected_run_id=124, current_control_sha=sha))
    reject(lambda: verify_run(run, [{"name": "offline-contract", "conclusion": "success"}],
                              expected_run_id=123, current_control_sha=sha))
    reject(lambda: verify_run(run, jobs * 2, expected_run_id=123,
                              current_control_sha=sha))
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / "repo"
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit",
                        "--allow-empty", "-qm", "base"], check=True)
        base = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                       text=True).strip()
        proof = root / TARGET
        proof.parent.mkdir(parents=True)
        proof.write_text("OpenHands Issue #220 distance(a,b). This does not change behavior.\n")
        patch = pathlib.Path(tmp) / "proof.patch"
        prepare(root, base, patch)
        proof.unlink()
        checked_base, checked_proof = validate_patch(root, patch)
        assert checked_base == base and checked_proof.read_text().startswith("OpenHands")
        reject(lambda: validate_patch(root, patch))
    print("PASS: source run provenance and exact patch replay; no writes to GitHub")


if __name__ == "__main__":
    main()
