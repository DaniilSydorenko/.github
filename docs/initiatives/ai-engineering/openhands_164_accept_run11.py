"""Protected accepted Run 11 release; never invokes a model."""
import json
import os
from urllib.request import Request, urlopen
from github_ref_lease import Controller, GitHubRefStore
from openhands_164_production_gates import verify_isolated_g3_evidence

HEAD = "d1d392a8b47054afca3236c072169e2cacc5816f"

def get(path, token):
    req = Request("https://api.github.com/repos/DaniilSydorenko/" + path,
                  headers={"Accept": "application/vnd.github+json",
                           **({"Authorization": "Bearer " + token} if token else {})})
    with urlopen(req, timeout=15) as response:
        return json.load(response)

def main():
    if verify_isolated_g3_evidence(217) is not None:
        raise SystemExit("STOP: protected G3 evidence missing")
    run = get(".github/actions/runs/45584278027", os.environ["GH_TOKEN"])
    pr = get("haversine-geolocation/pulls/230", None)
    head = "89b5a881435d06bba12d80a510b67908910c5815"
    if not (run.get("id") == 45584278027 and run.get("status") == "completed"
            and pr.get("number") == 230 and pr.get("merged") is True
            and pr.get("head", {}).get("sha") == head):
        raise SystemExit("STOP: accepted terminal result not proven")
    checks = get("haversine-geolocation/commits/" + head + "/check-runs?per_page=100", None)
    for name in ("Test and build", "Gitleaks"):
        matches = [c for c in checks["check_runs"] if c["name"] == name]
        if not matches or any(c["conclusion"] != "success" for c in matches):
            raise SystemExit("STOP: required check not successful: " + name)
    store = GitHubRefStore("DaniilSydorenko/.github", os.environ["AI_ENG_LEASE_WRITER_TOKEN"])
    snap = store.read()
    if snap.sha != HEAD or snap.state["phase"] != "VERIFYING" or snap.state["pr_url"] != "https://github.com/DaniilSydorenko/haversine-geolocation/pull/230":
        raise SystemExit("STOP: lease snapshot mismatch")
    print(Controller(store).release_verified("openhands-164-issue-217-correction-9",
          provider_terminal=True, integration_accepted=True, manual_approval=True))

if __name__ == "__main__":
    main()
