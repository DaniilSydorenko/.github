"""Read-only candidate audit for a personal-repo GitHub ruleset lease.

This is deliberately NOT a launch gate. Two distinct ACTIVE, exact-ref rulesets
may provide exclusive App updates plus no-force/no-delete, but GitHub admin
readback and positive/negative provider tests are still mandatory before the
existing classic-protection launch guard can ever be revised.

Never print bypass actor inventory, API tokens, or private product metadata.
"""
from __future__ import annotations

import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from lease_ref_protection import API, REF, REPO

SHA = re.compile(r"[0-9a-f]{40}\\Z")
EXPECTED_REF = "refs/heads/" + REF


def result(status: str, reason: str) -> dict:
    return {
        "status": status, "reason": reason, "candidate_only": True,
        "cursor_launch_authorized": False, "model_runs_started": 0,
        "github_mutated": False,
    }


def _exact_ref_rule(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    if (item.get("target") != "branch"
            or item.get("source_type") != "Repository"
            or item.get("source") != REPO
            or item.get("enforcement") != "active"):
        return False
    conditions = item.get("conditions")
    refs = conditions.get("ref_name") if isinstance(conditions, dict) else None
    return (isinstance(refs, dict)
            and refs.get("include") == [EXPECTED_REF]
            and refs.get("exclude") == [])


def audit(branch: object, rulesets: object, *, approved_app_id: object) -> dict:
    """Classify a configuration CANDIDATE, never verified dispatch authority.

    Callers must provide an authenticated complete ruleset detail inventory;
    public GitHub responses often hide bypass_actors without admin permissions.
    """
    if (not isinstance(branch, dict) or branch.get("name") != REF
            or branch.get("protected") is not True
            or not isinstance(branch.get("commit"), dict)
            or not isinstance(branch["commit"].get("sha"), str)
            or SHA.fullmatch(branch["commit"]["sha"]) is None):
        return result("STOP", "unprotected_or_unknown_lease_branch")
    if (type(approved_app_id) is not int or approved_app_id <= 0):
        return result("STOP", "approved_app_identity_unverified")
    if not isinstance(rulesets, list) or len(rulesets) >= 100:
        return result("STOP", "ruleset_inventory_unavailable_or_truncated")
    if any(not isinstance(item, dict) for item in rulesets):
        return result("STOP", "malformed_ruleset_inventory")
    exact = [item for item in rulesets if _exact_ref_rule(item)]
    if len(exact) != 2:
        return result("STOP", "two_independent_exact_active_rulesets_not_proven")
    ids = [item.get("id") for item in exact]
    if any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != 2:
        return result("STOP", "ruleset_identity_unverified")

    updates, guards = [], []
    for item in exact:
        rules = item.get("rules")
        bypass = item.get("bypass_actors")
        if not isinstance(rules, list) or not isinstance(bypass, list):
            return result("STOP", "rule_details_or_bypass_inventory_hidden")
        types = [r.get("type") for r in rules if isinstance(r, dict)]
        if len(types) != len(rules) or len(types) != len(set(types)):
            return result("STOP", "rules_unknown_or_duplicated")
        if types == ["update"]:
            updates.append(bypass)
        elif set(types) == {"deletion", "non_fast_forward"} and len(types) == 2:
            guards.append(bypass)
        else:
            return result("STOP", "unexpected_or_mixed_lease_rules")
    if len(updates) != 1 or len(guards) != 1:
        return result("STOP", "lease_update_and_guard_rules_not_separate")
    if guards[0]:
        return result("STOP", "non_fast_forward_or_deletion_has_bypass")
    if len(updates[0]) != 1 or not isinstance(updates[0][0], dict):
        return result("STOP", "not_one_exclusive_app_writer")
    writer = updates[0][0]
    if (set(writer) - {"actor_id", "actor_type", "bypass_mode"}
            or writer.get("actor_type") != "Integration"
            or writer.get("actor_id") != approved_app_id
            or writer.get("bypass_mode") != "always"):
        return result("STOP", "exclusive_app_writer_not_attested")
    return result("CANDIDATE", "ruleset_shape_passed_live_bypass_and_cas_proofs_still_required")


class ReadOnly:
    def __init__(self, token: str):
        self.token = token

    def get(self, path: str):
        if not (path == f"/branches/{REF}"
                or path == "/rulesets?includes_parents=false&per_page=100"
                or re.fullmatch(r"/rulesets/[1-9][0-9]*", path)):
            raise ValueError("unapproved GitHub GET endpoint")
        req = Request(API + path, method="GET", headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + self.token,
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urlopen(req, timeout=12) as response:
            return json.load(response)


def public_readonly_probe(reader: ReadOnly, approved_app_id: object) -> dict:
    try:
        branch = reader.get(f"/branches/{REF}")
        if not isinstance(branch, dict) or branch.get("protected") is not True:
            return result("STOP", "unprotected_or_unknown_lease_branch")
        listing = reader.get("/rulesets?includes_parents=false&per_page=100")
        if not isinstance(listing, list) or len(listing) >= 100:
            return result("STOP", "ruleset_inventory_unavailable_or_truncated")
        if any(not isinstance(x, dict) or type(x.get("id")) is not int
               or x["id"] <= 0 for x in listing):
            return result("STOP", "ruleset_identity_unverified")
        details = [reader.get(f"/rulesets/{x['id']}") for x in listing]
        return audit(branch, details, approved_app_id=approved_app_id)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError,
            TypeError, KeyError):
        return result("STOP", "ruleset_provider_evidence_unavailable")


def main() -> int:
    token = os.getenv("GITHUB_TOKEN")
    raw = os.getenv("AI_ENG_APPROVED_WRITER_APP_ID", "")
    app_id = int(raw) if raw.isdecimal() and len(raw) <= 15 else None
    status = (public_readonly_probe(ReadOnly(token), app_id)
              if token else result("STOP", "github_token_missing"))
    print(json.dumps(status, sort_keys=True))
    return 0 if status["status"] == "CANDIDATE" else 2


if __name__ == "__main__":
    sys.exit(main())
