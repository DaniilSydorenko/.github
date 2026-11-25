#!/usr/bin/env python3
"""Offline negative and positive checks for the one-shot rejected release."""
from github_ref_lease import Controller, LeaseError, Snapshot, initial_state, fingerprint, agent_id_for

HEAD = "409e9fe50a4fbf086f6a765f8b758bd6908e1af9"
RID = "openhands-164-issue-217-recovery-8"

class Store:
    def __init__(self):
        self.state = {**initial_state(), "revision": 10, "phase": "VERIFYING",
                      "request_id": RID, "agent_id": agent_id_for(RID),
                      "run_id": "run-45493386830",
                      "pr_url": "https://github.com/DaniilSydorenko/haversine-geolocation/pull/229",
                      "source_issue_url": "https://github.com/DaniilSydorenko/haversine-geolocation/issues/217",
                      "consumed_request_hashes": ["844221e53befae396f137bc06ad6cd86d6cf52cec98c5c27f9761e67da5959b2","7602adf7726fc3235b6afe4e80cd6f52241e8afc672fb854cc05a4b0ca778dcb","cbb61385736f96fef891ba34da95e9e1d096f6446900c3c71e4eaeac82e5040e"]}
        self.sha = HEAD
    def read(self):
        return Snapshot(self.sha, "a" * 40, self.state)
    def advance(self, observed, state):
        assert observed.sha == self.sha
        self.state = state
        self.sha = "b" * 40

def self_test():
    store = Store()
    ctl = Controller(store)
    args = dict(expected_sha=HEAD, provider_terminal=True, pr_closed_unmerged=True, manual_approval=True)
    for key in ("provider_terminal", "pr_closed_unmerged", "manual_approval", "expected_sha"):
        try:
            ctl.release_rejected_run9(**{**args, key: False})
        except LeaseError:
            pass
        else:
            raise AssertionError(key)
    assert ctl.release_rejected_run9(**args) == "REJECTED_RELEASED"
    assert store.state["phase"] == "IDLE" and store.state["revision"] == 11
    assert store.state["consumed_request_hashes"] == ["844221e53befae396f137bc06ad6cd86d6cf52cec98c5c27f9761e67da5959b2","7602adf7726fc3235b6afe4e80cd6f52241e8afc672fb854cc05a4b0ca778dcb","cbb61385736f96fef891ba34da95e9e1d096f6446900c3c71e4eaeac82e5040e"]
    try:
        ctl.release_rejected_run9(**args)
    except LeaseError:
        pass
    else:
        raise AssertionError("replay accepted")

if __name__ == "__main__":
    self_test()
    print("PASS: rejected release preserves ledger and rejects replay")
