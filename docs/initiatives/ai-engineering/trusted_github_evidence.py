#!/usr/bin/env python3
"""Task-local, read-only GitHub evidence collector (stdlib only).

Observes API-backed facts for one owner-authorized Issue. Semantic reviewer
assertions (PR relation, writer idle, owner permission, inventory completeness)
are never invented from Issue text or partial API data.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

SHA = re.compile(r"^[0-9a-f]{40}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
API = "https://api.github.com"

# Reviewer-only fields the decision gate expects; never auto-populated here.
REVIEWER_ASSERTION_FIELDS = (
    "related_inventory_complete",
    "related_prs[].relation",
    "writer",
    "scope",
    "owner_permission",
    "owner_gate",
    "accepted_implementation_shas",
)


@dataclass
class GitHubHTTPError(Exception):
    status: int
    path: str
    message: str = ""

    def __str__(self) -> str:
        return f"HTTP {self.status} for {self.path}: {self.message}"


@dataclass
class FakeGitHub:
    """Injectable transport for deterministic tests (no network)."""

    routes: Mapping[Tuple[str, str], Any] = field(default_factory=dict)
    dynamic: Optional[Callable[[str, str, Optional[Dict[str, str]]], Any]] = None
    calls: List[Tuple[str, str, Optional[Dict[str, str]]]] = field(default_factory=list)

    def get_json(self, path: str, params: Optional[Dict[str, str]] = None) -> Any:
        self.calls.append(("GET", path, params))
        if self.dynamic is not None:
            return self.dynamic("GET", path, params)
        key = ("GET", path)
        if key not in self.routes:
            raise GitHubHTTPError(404, path, "route not registered in fake transport")
        entry = self.routes[key]
        if isinstance(entry, Exception):
            raise entry
        if callable(entry):
            return entry(params)
        return entry


class LiveGitHub:
    """Authorized read-only GitHub REST client when a token is available."""

    def __init__(self, token: str, timeout: float = 30.0):
        self._token = token
        self._timeout = timeout

    def get_json(self, path: str, params: Optional[Dict[str, str]] = None) -> Any:
        if not path.startswith("/"):
            path = "/" + path
        url = API + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "trusted-github-evidence-collector/0.1",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise GitHubHTTPError(exc.code, path, detail) from exc
        except urllib.error.URLError as exc:
            raise GitHubHTTPError(0, path, str(exc.reason)) from exc


def client_from_environment() -> Tuple[Optional[Any], Optional[str]]:
    """Return (client, missing_capability) — never logs or persists secrets."""
    import os

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return None, "authenticated_github_read (no GITHUB_TOKEN or GH_TOKEN in runtime)"
    return LiveGitHub(token), None


def _parse_repo(repository: str) -> Tuple[str, str]:
    if not REPO.fullmatch(repository):
        raise ValueError("invalid repository slug")
    owner, name = repository.split("/", 1)
    return owner, name


def _issue_path(owner: str, name: str, issue_number: int) -> str:
    return f"/repos/{owner}/{name}/issues/{issue_number}"


def _paginate_events(
    transport: Any,
    owner: str,
    name: str,
    issue_number: int,
    *,
    per_page: int,
    max_pages: int,
) -> Tuple[List[dict], bool]:
    """Return (events, pagination_complete)."""
    collected: List[dict] = []
    for page in range(1, max_pages + 1):
        path = _issue_path(owner, name, issue_number) + "/events"
        batch = transport.get_json(path, {"per_page": str(per_page), "page": str(page)})
        if not isinstance(batch, list):
            raise GitHubHTTPError(502, path, "events response is not a list")
        collected.extend(batch)
        if len(batch) < per_page:
            return collected, True
    return collected, False


def _pr_numbers_from_events(events: Sequence[dict]) -> List[int]:
    seen = set()
    numbers: List[int] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        if ev.get("event") in ("connected", "cross-referenced", "referenced"):
            src = ev.get("source", {})
            if isinstance(src, dict) and src.get("type") == "issue":
                issue = src.get("issue", {})
                if (
                    isinstance(issue, dict)
                    and "pull_request" in issue
                    and isinstance(issue.get("number"), int)
                ):
                    num = issue["number"]
                    if num not in seen:
                        seen.add(num)
                        numbers.append(num)
        commit_id = ev.get("commit_id")
        if isinstance(commit_id, str) and ev.get("event") == "referenced":
            pass  # commit reference only; PR identity comes from source.issue above
    return numbers


def _parse_issue_body_pr_refs(body: str, repository: str) -> List[int]:
    """Unverified text references — not treated as observed inventory."""
    if not isinstance(body, str):
        return []
    owner, name = _parse_repo(repository)
    prefix = f"https://github.com/{owner}/{name}/pull/"
    found: List[int] = []
    seen = set()
    for match in re.finditer(rf"{re.escape(prefix)}([1-9][0-9]*)", body):
        num = int(match.group(1))
        if num not in seen:
            seen.add(num)
            found.append(num)
    for match in re.finditer(r"#([1-9][0-9]*)", body):
        num = int(match.group(1))
        if num not in seen:
            seen.add(num)
            found.append(num)
    return found


def _fetch_pull(
    transport: Any,
    owner: str,
    name: str,
    number: int,
) -> dict:
    path = f"/repos/{owner}/{name}/pulls/{number}"
    data = transport.get_json(path)
    if not isinstance(data, dict):
        raise GitHubHTTPError(502, path, "pull response is not an object")
    return data


def _observed_pr_record(pull: dict, *, files_complete: bool, files: Sequence[str]) -> dict:
    head = pull.get("head") if isinstance(pull.get("head"), dict) else {}
    base = pull.get("base") if isinstance(pull.get("base"), dict) else {}
    head_sha = head.get("sha")
    record = {
        "number": pull.get("number"),
        "state": pull.get("state"),
        "merged": bool(pull.get("merged_at")),
        "head_ref": head.get("ref"),
        "base_ref": base.get("ref"),
        "head_sha": head_sha if isinstance(head_sha, str) else None,
        "head_sha_observed": isinstance(head_sha, str) and SHA.fullmatch(head_sha) is not None,
        "changed_files_observed": list(files),
        "changed_files_pagination_complete": files_complete,
    }
    return record


def _fetch_pull_files(
    transport: Any,
    owner: str,
    name: str,
    number: int,
    *,
    per_page: int,
    max_pages: int,
) -> Tuple[List[str], bool]:
    names: List[str] = []
    for page in range(1, max_pages + 1):
        path = f"/repos/{owner}/{name}/pulls/{number}/files"
        batch = transport.get_json(path, {"per_page": str(per_page), "page": str(page)})
        if not isinstance(batch, list):
            raise GitHubHTTPError(502, path, "files response is not a list")
        for item in batch:
            if isinstance(item, dict) and isinstance(item.get("filename"), str):
                names.append(item["filename"])
        if len(batch) < per_page:
            return names, True
    return names, False


def _recent_default_commits(
    transport: Any,
    owner: str,
    name: str,
    branch: str,
    *,
    limit: int,
) -> List[str]:
    path = f"/repos/{owner}/{name}/commits"
    batch = transport.get_json(path, {"sha": branch, "per_page": str(limit)})
    if not isinstance(batch, list):
        raise GitHubHTTPError(502, path, "commits response is not a list")
    shas: List[str] = []
    for item in batch:
        if isinstance(item, dict) and isinstance(item.get("sha"), str) and SHA.fullmatch(item["sha"]):
            shas.append(item["sha"])
    return shas


def collect_task_evidence(
    repository: str,
    issue_number: int,
    *,
    transport: Optional[Any] = None,
    explicit_pr_numbers: Optional[Sequence[int]] = None,
    max_event_pages: int = 3,
    max_file_pages: int = 2,
    max_prs: int = 10,
    commit_sample: int = 15,
    verify_default_sha_twice: bool = True,
) -> dict:
    """Collect bounded read-only evidence for one Issue.

    Returns a envelope with API ``observed_facts``, explicit ``unknowns``,
    and ``status`` of OBSERVED, PARTIAL, or NEEDS_EVIDENCE. Never emits READY
    or fabricates reviewer attestation fields.
    """
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    missing: List[str] = []
    warnings: List[str] = []

    if transport is None:
        transport, cap = client_from_environment()
        if transport is None:
            return {
                "status": "NEEDS_EVIDENCE",
                "missing_capabilities": [cap],
                "observed_at": started,
                "observed_facts": {},
                "reviewer_assertions_required": list(REVIEWER_ASSERTION_FIELDS),
                "warnings": ["No live GitHub read performed"],
            }

    try:
        owner, name = _parse_repo(repository)
    except ValueError:
        return {
            "status": "NEEDS_EVIDENCE",
            "missing_capabilities": [],
            "observed_at": started,
            "observed_facts": {},
            "reviewer_assertions_required": list(REVIEWER_ASSERTION_FIELDS),
            "warnings": ["Invalid repository slug"],
        }

    observed: Dict[str, Any] = {
        "repo": repository,
        "issue_number": issue_number,
    }

    try:
        repo_meta = transport.get_json(f"/repos/{owner}/{name}")
        if not isinstance(repo_meta, dict):
            raise GitHubHTTPError(502, f"/repos/{owner}/{name}", "invalid repo metadata")
        default_branch = repo_meta.get("default_branch")
        if not isinstance(default_branch, str) or not default_branch:
            missing.append("default_branch_name")
            default_branch = None

        issue = transport.get_json(_issue_path(owner, name, issue_number))
        if not isinstance(issue, dict):
            raise GitHubHTTPError(502, _issue_path(owner, name, issue_number), "invalid issue")
        if issue.get("number") != issue_number:
            warnings.append("Issue number mismatch between request and response")
        issue_state = issue.get("state")
        if issue_state not in ("open", "closed"):
            missing.append("issue_state")
        observed["issue_state"] = issue_state if issue_state in ("open", "closed") else None

        unverified_body_prs = _parse_issue_body_pr_refs(issue.get("body") or "", repository)
        observed["unverified_issue_text_pr_references"] = unverified_body_prs

        default_sha = None
        if default_branch:
            ref = transport.get_json(f"/repos/{owner}/{name}/git/ref/heads/{default_branch}")
            if isinstance(ref, dict) and isinstance(ref.get("object"), dict):
                sha = ref["object"].get("sha")
                if isinstance(sha, str) and SHA.fullmatch(sha):
                    default_sha = sha
            if default_sha is None:
                missing.append("default_branch_sha")

        observed["default_branch"] = default_branch
        observed["default_sha"] = default_sha

        if verify_default_sha_twice and default_branch and default_sha:
            ref2 = transport.get_json(f"/repos/{owner}/{name}/git/ref/heads/{default_branch}")
            sha2 = None
            if isinstance(ref2, dict) and isinstance(ref2.get("object"), dict):
                maybe = ref2["object"].get("sha")
                if isinstance(maybe, str) and SHA.fullmatch(maybe):
                    sha2 = maybe
            if sha2 and sha2 != default_sha:
                warnings.append("Default branch SHA changed during collection")
                observed["default_sha"] = sha2
                observed["default_sha_at_start"] = default_sha
                default_sha = sha2

        events, events_complete = _paginate_events(
            transport, owner, name, issue_number, per_page=100, max_pages=max_event_pages
        )
        observed["issue_events_pagination_complete"] = events_complete
        if not events_complete:
            warnings.append("Issue event pagination truncated (bounded max pages)")

        linked = _pr_numbers_from_events(events)
        if explicit_pr_numbers:
            for num in explicit_pr_numbers:
                if num not in linked:
                    linked.append(num)
        linked = linked[:max_prs]
        observed["linked_pr_numbers_from_events"] = list(linked)

        related_prs: List[dict] = []
        pr_fetch_incomplete = False
        for num in linked:
            pull = _fetch_pull(transport, owner, name, num)
            if pull.get("number") != num:
                warnings.append(f"PR response number mismatch for #{num}")
            files, files_complete = _fetch_pull_files(
                transport, owner, name, num, per_page=100, max_pages=max_file_pages
            )
            if not files_complete:
                pr_fetch_incomplete = True
            record = _observed_pr_record(pull, files_complete=files_complete, files=files)
            pull_verify = _fetch_pull(transport, owner, name, num)
            vhead = (
                pull_verify.get("head", {}).get("sha")
                if isinstance(pull_verify.get("head"), dict)
                else None
            )
            if (
                isinstance(record.get("head_sha"), str)
                and isinstance(vhead, str)
                and record["head_sha"] != vhead
            ):
                warnings.append(f"PR #{num} HEAD changed during collection")
                record["head_sha_at_start"] = record["head_sha"]
                record["head_sha"] = vhead
                record["head_sha_observed"] = SHA.fullmatch(vhead) is not None
            if pull_verify.get("merged_at") and record.get("state") == "open":
                warnings.append(f"PR #{num} merged during collection")
                record["state"] = pull_verify.get("state")
                record["merged"] = True
            related_prs.append(record)

        observed["related_prs"] = related_prs
        observed["related_prs_files_pagination_complete"] = not pr_fetch_incomplete

        commit_shas: List[str] = []
        if default_branch:
            commit_shas = _recent_default_commits(
                transport, owner, name, default_branch, limit=commit_sample
            )
        observed["default_branch_recent_commit_shas"] = commit_shas
        observed["accepted_shas"] = None  # semantic; requires reviewer proof mapping

        status = "OBSERVED"
        if missing:
            status = "NEEDS_EVIDENCE"
        elif not events_complete or pr_fetch_incomplete:
            status = "PARTIAL"
            missing.append("complete_bounded_inventory")

        return {
            "status": status,
            "missing_capabilities": missing,
            "observed_at": started,
            "observed_facts": observed,
            "reviewer_assertions_required": list(REVIEWER_ASSERTION_FIELDS),
            "warnings": warnings,
        }

    except GitHubHTTPError as exc:
        cap = f"github_api_read_http_{exc.status}"
        if exc.status in (403, 429):
            cap = "github_api_rate_limit_or_permission_denied"
        elif exc.status == 404:
            cap = "github_api_not_found_or_repo_issue_mismatch"
        return {
            "status": "NEEDS_EVIDENCE",
            "missing_capabilities": [cap],
            "observed_at": started,
            "observed_facts": observed,
            "reviewer_assertions_required": list(REVIEWER_ASSERTION_FIELDS),
            "warnings": warnings + [str(exc)],
        }


def build_reconcile_observed(collected: dict) -> dict:
    """Map collector output to ``evidence_reconcile`` observed shape.

    Omits reviewer-attested fields (``related_inventory_complete``). Never
    upgrades PARTIAL/NEEDS_EVIDENCE collection into a complete inventory.
    """
    facts = collected.get("observed_facts") or {}
    prs = []
    for pr in facts.get("related_prs") or []:
        if not isinstance(pr, dict):
            continue
        prs.append(
            {
                "number": pr.get("number"),
                "head_sha": pr.get("head_sha"),
                "state": "open" if pr.get("state") == "open" and not pr.get("merged") else "closed",
            }
        )
    return {
        "repo": facts.get("repo"),
        "issue_number": facts.get("issue_number"),
        "issue_state": facts.get("issue_state"),
        "default_sha": facts.get("default_sha"),
        "related_prs": prs,
        # Reviewer must attest completeness after classifying relevant PRs.
        "related_inventory_complete": None,
        "accepted_shas": [],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(argv or sys.argv[1:])
    if len(argv) != 2:
        print(
            "Usage: python3 trusted_github_evidence.py <owner/repo> <issue-number>",
            file=sys.stderr,
        )
        return 2
    repository, issue_s = argv
    try:
        issue_number = int(issue_s)
    except ValueError:
        print("Issue number must be an integer", file=sys.stderr)
        return 2
    result = collect_task_evidence(repository, issue_number)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "OBSERVED" else 1


if __name__ == "__main__":
    sys.exit(main())
