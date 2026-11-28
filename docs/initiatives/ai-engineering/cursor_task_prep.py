"""Read-only automatic task preparation (#229, OPS-2). Deterministic; no model call.

Input: a repository and ordered issue numbers. Output: a per-issue proposal
(allowed paths, paired tests, risk class, competing PRs, acceptance hints,
owner questions) and, when every task is unambiguous and low risk, a
``queue_request`` ready for the reviewer-gated ``submit-queue`` action.

A proposal is never authority: issue text is untrusted data, it can only name
files that already exist at the default head, and every proposal is re-validated
by ``submit-queue`` (``cursor_queue_ops.build_spec``) when the owner submits it.
Public targets only while the control plane is public (see cursor_queue).
"""
from __future__ import annotations

import posixpath
import re
from typing import Any

from cursor_queue import ALLOWED_REPOSITORIES, QueueError

PATH_TOKEN = re.compile(r"(?<![A-Za-z0-9_./-])([A-Za-z0-9_.][A-Za-z0-9_./-]{0,180}\.[A-Za-z0-9]{1,6})(?![A-Za-z0-9_/-])")
CHECKBOX = re.compile(r"^\s*[-*]\s+\[[ xX]\]\s+(.{3,200})$", re.MULTILINE)
# Any match makes the task high risk: it always needs explicit owner review.
HIGH_RISK = re.compile(
    r"(^|/)\.github/|(^|/)\.cursor/|(^|/)(package(-lock)?\.json|pnpm-lock\.yaml|yarn\.lock|"
    r"Dockerfile|docker-compose[^/]*\.ya?ml|\.env[^/]*|.*\.tf)$|"
    r"(^|/)(infra|deploy|deployment|migrations?|release|secrets?)(/|$)|"
    r"auth|secret|token|credential|password|payment|billing",
    re.IGNORECASE)
TEST_DIRS = ("spec", "test", "tests", "__tests__")
SCOPE_HEADING = re.compile(r"^#{1,6}\s*(allowed (files|paths)|scope|files to change)\b.*$",
                           re.IGNORECASE | re.MULTILINE)


def scope_section(body: str) -> str | None:
    """Text of an explicit 'Allowed files' / 'Scope' section, if the issue has one."""
    m = SCOPE_HEADING.search(body or "")
    if not m:
        return None
    rest = body[m.end():]
    nxt = re.search(r"^#{1,6}\s", rest, re.MULTILINE)
    return rest[:nxt.start()] if nxt else rest


def is_high_risk(path: str) -> bool:
    # Markdown documentation is not high risk unless it governs the repo (.github, .cursor).
    if path.lower().endswith(".md") and not path.startswith((".github/", ".cursor/")):
        return False
    return HIGH_RISK.search(path) is not None
MAX_PATHS = 8


def _tree(gh: Any, repository: str, branch: str) -> set[str]:
    tree = gh.get_json(f"/repos/{repository}/git/trees/{branch}", {"recursive": "1"})
    entries = tree.get("tree") if isinstance(tree, dict) else None
    if not isinstance(entries, list) or tree.get("truncated") is True:
        raise QueueError("repository tree unreadable or truncated")
    return {e["path"] for e in entries if isinstance(e, dict) and e.get("type") == "blob"
            and isinstance(e.get("path"), str)}


def named_paths(text: str, tree: set[str]) -> list[str]:
    """Existing files the (untrusted) text names; nothing else, never '..'."""
    out = []
    for token in PATH_TOKEN.findall(text or ""):
        path = token.removeprefix("./")
        if ".." in path.split("/") or path.startswith("/") or path != posixpath.normpath(path):
            continue
        if path in tree and path not in out:
            out.append(path)
    return out[:MAX_PATHS]


def paired_tests(path: str, tree: set[str]) -> list[str]:
    """Existing spec/test files for a source file (same stem), in common layouts."""
    stem, ext = posixpath.splitext(posixpath.basename(path))
    if ext not in (".ts", ".tsx", ".js", ".jsx", ".vue", ".mjs", ".cjs", ".py"):
        return []
    names = {f"{stem}.spec{ext}", f"{stem}.test{ext}", f"{stem}.spec.ts", f"{stem}.test.ts",
             f"test_{stem}.py"}
    # Layouts that prefix the test with a source directory, e.g. src/v2/x.ts -> spec/v2-x.spec.ts
    for d in posixpath.dirname(path).split("/"):
        if d:
            names |= {f"{d}-{stem}.spec{ext}", f"{d}-{stem}.test{ext}"}
    found = sorted(p for p in tree if posixpath.basename(p) in names and p != path
                   and (posixpath.dirname(p) == posixpath.dirname(path)
                        or p.split("/", 1)[0] in TEST_DIRS
                        or any(f"/{d}/" in f"/{p}" for d in TEST_DIRS)))
    return found[:2]


def _competing(open_prs: list[Any], issue: int) -> list[int]:
    pattern = re.compile(rf"(?<![0-9A-Za-z/])#{issue}(?![0-9])")
    return sorted(p["number"] for p in open_prs if isinstance(p, dict)
                  and type(p.get("number")) is int
                  and pattern.search(f"{p.get('title') or ''}\n{p.get('body') or ''}"))


def prepare(gh: Any, repository: str, issues: list[int], *, queue_id: str) -> dict[str, Any]:
    if repository not in ALLOWED_REPOSITORIES:
        raise QueueError("repository not allowlisted")
    if (not isinstance(issues, list) or not issues or len(set(issues)) != len(issues)
            or any(type(n) is not int or n <= 0 for n in issues)):
        raise QueueError("issues must be distinct positive integers")
    repo = gh.get_json(f"/repos/{repository}")
    if not isinstance(repo, dict) or repo.get("private") is not False:
        # Before any further read: nothing about a private target reaches public logs.
        raise QueueError("private or unverifiable repository needs a private control plane")
    branch = repo.get("default_branch")
    tree = _tree(gh, repository, branch)
    open_prs = gh.get_json(f"/repos/{repository}/pulls", {"state": "open", "per_page": "100"})
    if not isinstance(open_prs, list) or len(open_prs) >= 100:
        raise QueueError("open pull request inventory incomplete")
    tasks, ready = [], True
    for n in issues:
        issue = gh.get_json(f"/repos/{repository}/issues/{n}")
        questions: list[str] = []
        if not isinstance(issue, dict) or "pull_request" in issue:
            raise QueueError(f"#{n} is not an issue")
        if issue.get("state") != "open":
            questions.append(f"#{n} is not open; remove it from the queue or reopen it.")
        body = issue.get("body") or ""
        # An explicit scope section wins over files the issue merely mentions.
        section = scope_section(body)
        text = section if section is not None else f"{issue.get('title') or ''}\n{body}"
        sources = named_paths(text, tree)
        tests = [t for s in sources for t in paired_tests(s, tree) if t not in sources]
        paths = sorted(set(sources) | set(tests))
        risk = "high" if any(is_high_risk(p) for p in paths) else "low"
        competing = _competing(open_prs, n)
        if not paths:
            questions.append(f"#{n} names no existing file; which files may change?")
        if competing:
            questions.append(f"#{n} is cited by open PR(s) {competing}; close or continue them first.")
        if risk == "high":
            questions.append(f"#{n} touches high-risk paths; confirm explicitly or narrow the scope.")
        if not any(p in tests or posixpath.basename(p).split(".")[0] in ("test", "spec")
                   or ".spec." in p or ".test." in p or p.startswith(TEST_DIRS) for p in paths):
            questions.append(f"#{n} has no existing test file in scope; name the regression test path.")
        ready = ready and not questions
        tasks.append({"issue": n, "title": issue.get("title"), "proposed_allowed_paths": paths,
                      "paired_tests": tests, "risk": risk, "competing_prs": competing,
                      "acceptance_hints": CHECKBOX.findall(issue.get("body") or "")[:10],
                      "questions": questions})
    out: dict[str, Any] = {
        "outcome": "PREPARED" if ready else "NEEDS_OWNER", "repository": repository,
        "default_branch": branch, "default_head_tree": "read", "tasks": tasks,
        "authority": "proposal_only; submit-queue in the reviewer-gated workflow authorizes",
    }
    if ready:
        out["queue_request"] = {"queue_id": queue_id, "repository": repository, "issues": issues,
                                "allowed_paths": {str(t["issue"]): t["proposed_allowed_paths"]
                                                  for t in tasks}}
    return out
