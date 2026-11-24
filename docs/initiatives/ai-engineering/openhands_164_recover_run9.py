"""Protected one-shot rejected Run 9 recovery; never invokes a model."""
import json
import os
from urllib.request import Request, urlopen
from github_ref_lease import Controller, GitHubRefStore
from openhands_164_production_gates import verify_isolated_g3_evidence

HEAD = "409e9fe50a4fbf086f6a765f8b758bd6908e1af9"

def get(path, token):
    req = Request("https://api.github.com/repos/DaniilSydorenko/" + path,
                  headers={"Authorization": "Bearer " + token,
                           "Accept": "application/vnd.github+json"})
    with urlopen(req, timeout=15) as response:
        return json.load(response)

def main():
    if verify_isolated_g3_evidence(217) is not None:
        raise SystemExit("STOP: protected G3 evidence missing")
    token = os.environ["GH_TOKEN"]
    run = get(".github/actions/runs/45493386830", token)
    # Public target repository; HQ token is read-only and cannot mutate it.
    pr = get("haversine-geolocation/pulls/229", token)
    if not (run.get("id") == 45493386830 and run.get("status") == "completed"
            and run.get("conclusion") == "failure"
            and pr.get("number") == 229 and pr.get("state") == "closed"
            and pr.get("merged") is False
            and pr.get("head", {}).get("sha") == "b6c27048fa935102a4874773eccdbea4b3c5b2fd"):
        raise SystemExit("STOP: terminal rejected result not proven")
    store = GitHubRefStore("DaniilSydorenko/.github", os.environ["AI_ENG_LEASE_WRITER_TOKEN"])
    print(Controller(store).release_rejected_run9(expected_sha=HEAD,
          provider_terminal=True, pr_closed_unmerged=True, manual_approval=True))

if __name__ == "__main__":
    main()
