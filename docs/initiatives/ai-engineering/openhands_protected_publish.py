#!/usr/bin/env python3
"""Verify provenance and exact one-file patch before a separately approved Draft PR.

No OpenRouter secret, model invocation, or GitHub mutation in this module.
The publisher's GitHub token belongs ONLY to its protected workflow job.
"""
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

from openhands_draft_handoff import TARGET, plan
from openhands_artifact_verifier import verify
from openhands_draft_publisher import publish_verified_proof, _PROTECTED_AUTHORITY

CONTROL = "DaniilSydorenko/.github"
TARGET_REPO = "DaniilSydorenko/haversine-geolocation"
WORKFLOW = ".github/workflows/ai-eng-openhands-readiness.yml"


def verify_run(run, jobs, *, expected_run_id, current_control_sha):
    if type(expected_run_id) is not int or expected_run_id < 1:
        raise ValueError("invalid_run_id")
    if not isinstance(run, dict) or run.get("id") != expected_run_id:
        raise ValueError("run_identity_mismatch")
    if run.get("repository", {}).get("full_name") != CONTROL:
        raise ValueError("wrong_source_repo")
    if run.get("path") != WORKFLOW:
        raise ValueError("wrong_source_workflow")
    if run.get("event") != "workflow_dispatch" or run.get("head_branch") != "main":
        raise ValueError("wrong_source_event")
    if run.get("actor", {}).get("login") != "DaniilSydorenko":
        raise ValueError("wrong_source_actor")
    if run.get("conclusion") != "success" or run.get("run_attempt") != 1:
        raise ValueError("source_run_not_successful")
    if run.get("head_sha") != current_control_sha:
        raise ValueError("source_workflow_sha_stale")
    if not isinstance(jobs, list):
        raise ValueError("invalid_source_jobs")
    live = [j for j in jobs if j.get("name") == "manual-pilot-live-execute"]
    if len(live) != 1 or live[0].get("conclusion") != "success":
        raise ValueError("live_executor_job_not_proven")
    return True


def validate_patch(workspace, patch_path):
    root = pathlib.Path(workspace).resolve(strict=True)
    patch = pathlib.Path(patch_path).resolve(strict=True)
    if patch.is_symlink() or not patch.is_file() or patch.stat().st_size > 20000:
        raise ValueError("invalid_patch_artifact")
    base = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                   text=True, timeout=15).strip()
    # A patch is not trusted merely because it came from a successful workflow.
    flags = dict(approved=True, lease=True, budget=True, writer=True, collision_clear=True)
    if plan(patch, base, **flags)["decision"] != "READY_FOR_PROTECTED_PUBLISHER":
        raise ValueError("patch_contract_rejected")
    if (root / TARGET).exists():
        raise ValueError("target_already_exists")
    subprocess.run(["git", "-C", str(root), "apply", "--check", str(patch)],
                   check=True, capture_output=True, timeout=15)
    subprocess.run(["git", "-C", str(root), "apply", str(patch)],
                   check=True, capture_output=True, timeout=15)
    status = subprocess.check_output(
        ["git", "-C", str(root), "status", "--porcelain=v1", "--untracked-files=all"],
        text=True, timeout=15).splitlines()
    if status != ["?? " + TARGET]:
        raise ValueError("unexpected_worktree_changes")
    proof = root / TARGET
    if proof.is_symlink() or not proof.is_file() or not verify(
            [TARGET], proof.read_text(encoding="utf-8")).startswith("PASS:"):
        raise ValueError("invalid_proof")
    return base, proof


def github_get(url, token):
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"}, method="GET")
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def main():
    if len(sys.argv) != 5 or sys.argv[1] != "--publish":
        sys.exit("Usage: --publish SOURCE_RUN_ID TARGET_CHECKOUT PATCH")
    run_id = int(sys.argv[2])
    target = sys.argv[3]
    patch = sys.argv[4]
    if not all((os.environ.get("GITHUB_REPOSITORY") == CONTROL,
                os.environ.get("GITHUB_ACTOR") == "DaniilSydorenko",
                os.environ.get("GITHUB_REF") == "refs/heads/main",
                os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch",
                os.environ.get("GITHUB_RUN_ATTEMPT") == "1")):
        sys.exit("STOP: untrusted_publisher_context")
    token = os.environ.get("GH_TOKEN", "")
    if not token:
        sys.exit("STOP: missing_publisher_token")
    api = "https://api.github.com/repos/" + CONTROL
    run = github_get(api + "/actions/runs/" + str(run_id), token)
    jobs_payload = github_get(api + "/actions/runs/" + str(run_id) + "/jobs?per_page=100", token)
    if jobs_payload.get("total_count", 101) > 100:
        sys.exit("STOP: source_job_inventory_incomplete")
    control_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, timeout=15).strip()
    verify_run(run, jobs_payload["jobs"], expected_run_id=run_id,
               current_control_sha=control_sha)
    base, proof = validate_patch(target, patch)
    # Revalidate target scope and PR collisions with fresh GitHub GET before writes.
    from openhands_issue_contract import live_preflight
    if live_preflight().get("reason") != "scope_preflight_passed_but_live_gates_unverified":
        sys.exit("STOP: target_scope_collision")
    # The publisher module re-checks master SHA, duplicate branch PR and
    # creates exactly one branch, one file and one Draft PR.
    result = publish_verified_proof(token=token, base_sha=base, proof_path=proof,
                                    authority=_PROTECTED_AUTHORITY)
    print(json.dumps({"decision": "DRAFT_PR_CREATED",
                      "url": result.get("html_url"), "source_run_id": run_id}))


if __name__ == "__main__":
    main()
