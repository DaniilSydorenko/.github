"""Protected accepted pilot release; never invokes a model."""
import json
import os
from urllib.request import Request, urlopen
from github_ref_lease import Controller, GitHubRefStore
from openhands_164_production_gates import verify_isolated_g3_evidence


def get(path, token):
    req = Request("https://api.github.com/repos/DaniilSydorenko/" + path,
                  headers={"Accept": "application/vnd.github+json",
                           **({"Authorization": "Bearer " + token} if token else {})})
    with urlopen(req, timeout=15) as response:
        return json.load(response)

def main():
    import re
    from openhands_164_draft_publisher import branch_for
    issue = int(os.environ["AI_ENG_OWNER_GO_ISSUE"])
    if verify_isolated_g3_evidence(issue) is not None:
        raise SystemExit("STOP: protected G3 evidence missing")
    store = GitHubRefStore("DaniilSydorenko/.github", os.environ["AI_ENG_LEASE_WRITER_TOKEN"])
    snap = store.read()
    state = snap.state
    match = re.fullmatch(r"https://github.com/DaniilSydorenko/haversine-geolocation/pull/([1-9][0-9]*)", state.get("pr_url") or "")
    run_match = re.fullmatch(r"run-([1-9][0-9]*)", state.get("run_id") or "")
    head = os.environ.get("AI_ENG_ACCEPTED_HEAD", "")
    if state["phase"] != "VERIFYING" or not match or not run_match or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise SystemExit("STOP: active lease or owner head missing")
    run = get(".github/actions/runs/" + run_match[1], os.environ["GH_TOKEN"])
    pr = get("haversine-geolocation/pulls/" + match[1], None)
    if not (run.get("status") == "completed" and pr.get("merged") is True
            and pr.get("base", {}).get("ref") == "master"
            and pr.get("head", {}).get("ref") == branch_for(issue)
            and pr.get("head", {}).get("sha") == head):
        raise SystemExit("STOP: accepted terminal result not proven")
    checks = get("haversine-geolocation/commits/" + head + "/check-runs?per_page=100", None)
    for name in ("Test and build", "Gitleaks"):
        matches = [c for c in checks["check_runs"] if c["name"] == name]
        if not matches or any(c["conclusion"] != "success" for c in matches):
            raise SystemExit("STOP: required check not successful: " + name)
    if store.read().sha != snap.sha:
        raise SystemExit("STOP: lease changed")
    print(Controller(store).release_verified(state["request_id"],
          provider_terminal=True, integration_accepted=True, manual_approval=True))

if __name__ == "__main__":
    main()
