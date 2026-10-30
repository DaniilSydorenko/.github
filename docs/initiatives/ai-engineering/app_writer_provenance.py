"""Read-only provenance check for an owner-controlled GitHub App lease writer.

Does not authorize GitHub writes, Cursor calls, bypass creation, or a pilot.
Use only from a protected, owner-approved default-branch workflow after
actions/create-github-app-token minted a *read-scoped* installation token.
An app slug/ID or env flag alone is not proof of unique controller custody.
"""
from __future__ import annotations

import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from lease_ref_protection import REPO

REPO_ID = 1406421648
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{2,99}\Z")
BASE = "https://api.github.com"


def answer(status: str, reason: str) -> dict:
    return {
        "status": status, "reason": reason, "owner_review_required": True,
        "cursor_launch_authorized": False, "lease_write_authorized": False,
        "model_runs_started": 0, "github_mutated": False,
    }


def verify(app: object, scoped_repositories: object, *,
           expected_app_id: object, expected_slug: object,
           minted_app_slug: object, minted_installation_id: object) -> dict:
    """Strict metadata/scope check. Trusted runner must attest token minting."""
    if (type(expected_app_id) is not int or expected_app_id < 1
            or not isinstance(expected_slug, str)
            or SLUG.fullmatch(expected_slug) is None
            or minted_app_slug != expected_slug
            or type(minted_installation_id) is not int
            or minted_installation_id < 1):
        return answer("STOP", "app_or_mint_provenance_unverified")
    if (not isinstance(app, dict) or app.get("id") != expected_app_id
            or type(app.get("id")) is not int
            or app.get("slug") != expected_slug):
        return answer("STOP", "github_app_identity_mismatch")
    owner = app.get("owner")
    if (not isinstance(owner, dict) or owner.get("login") != "DaniilSydorenko"
            or owner.get("type") != "User"):
        return answer("STOP", "app_owner_unverified")
    perms = app.get("permissions")
    if (not isinstance(perms, dict) or perms.get("contents") != "write"
            or set(perms) - {"contents", "metadata"}):
        return answer("STOP", "app_has_missing_or_excessive_repository_permissions")
    if (not isinstance(scoped_repositories, dict)
            or type(scoped_repositories.get("total_count")) is not int
            or scoped_repositories["total_count"] != 1):
        return answer("STOP", "installation_token_not_scoped_to_one_repo")
    items = scoped_repositories.get("repositories")
    if not isinstance(items, list) or len(items) != 1:
        return answer("STOP", "installation_repository_inventory_incomplete")
    item = items[0]
    if (not isinstance(item, dict) or type(item.get("id")) is not int
            or item["id"] != REPO_ID or item.get("full_name") != REPO
            or item.get("private") is not False):
        return answer("STOP", "installation_token_repository_mismatch")
    return answer("CREDENTIAL_PATH_OBSERVED",
                  "scoped_app_token_metadata_matches_no_custody_or_live_cas_proof")


class AppMetadataReadOnly:
    def __init__(self, token: str):
        if not isinstance(token, str) or not token:
            raise ValueError("missing installation token")
        self._token = token

    def get(self, path: str) -> dict:
        if (path != "/installation/repositories?per_page=100"
                and not re.fullmatch(r"/apps/[a-z0-9][a-z0-9-]{2,99}", path)):
            raise ValueError("unapproved endpoint")
        req = Request(BASE + path, method="GET", headers={
            "Authorization": "Bearer " + self._token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urlopen(req, timeout=12) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise ValueError("unknown GitHub response")
        return result


def probe(reader: AppMetadataReadOnly, *, expected_app_id: object,
          expected_slug: object, minted_app_slug: object,
          minted_installation_id: object) -> dict:
    if (type(expected_app_id) is not int or expected_app_id < 1
            or not isinstance(expected_slug, str)
            or SLUG.fullmatch(expected_slug) is None
            or minted_app_slug != expected_slug
            or type(minted_installation_id) is not int
            or minted_installation_id < 1):
        return answer("STOP", "app_or_mint_provenance_unverified")
    try:
        app = reader.get("/apps/" + expected_slug)
        repos = reader.get("/installation/repositories?per_page=100")
        return verify(app, repos, expected_app_id=expected_app_id,
                      expected_slug=expected_slug,
                      minted_app_slug=minted_app_slug,
                      minted_installation_id=minted_installation_id)
    except (ValueError, TypeError, KeyError, HTTPError, URLError,
            TimeoutError, OSError):
        return answer("STOP", "trusted_github_app_metadata_unavailable")


def main() -> int:
    raw_id = os.getenv("AI_ENG_WRITER_APP_ID", "")
    raw_install = os.getenv("AI_ENG_MINTED_INSTALLATION_ID", "")
    token = os.getenv("AI_ENG_APP_PROBE_TOKEN", "")
    slug = os.getenv("AI_ENG_WRITER_APP_SLUG", "")
    minted_slug = os.getenv("AI_ENG_MINTED_APP_SLUG", "")
    app_id = int(raw_id) if raw_id.isdecimal() and len(raw_id) <= 15 else None
    installation_id = (int(raw_install) if raw_install.isdecimal()
                       and len(raw_install) <= 15 else None)
    if not token:
        result = answer("STOP", "trusted_installation_token_unavailable")
    else:
        result = probe(AppMetadataReadOnly(token), expected_app_id=app_id,
                       expected_slug=slug, minted_app_slug=minted_slug,
                       minted_installation_id=installation_id)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "CREDENTIAL_PATH_OBSERVED" else 2


if __name__ == "__main__":
    sys.exit(main())
