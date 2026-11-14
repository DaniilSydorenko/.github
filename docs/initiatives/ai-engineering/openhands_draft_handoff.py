#!/usr/bin/env python3
"""Draft-PR handoff for Issue #220. Offline plan only; no GitHub writes.

A separate protected, lease-holding publisher must consume this plan.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

ISSUE = 220
REPO = "DaniilSydorenko/haversine-geolocation"
TARGET = "docs/agent-pilot-proof.md"
BRANCH = "ai-eng/issue-220-openhands-proof"


def plan(patch, base_sha, *, approved=False, lease=False, budget=False,
         writer=False, collision_clear=False):
    if not re.fullmatch(r"[0-9a-f]{40}", base_sha):
        return {"decision": "STOP", "reason": "invalid_base_sha"}
    if not all((approved, lease, budget, writer, collision_clear)):
        return {"decision": "STOP", "reason": "authorization_or_collision_unverified"}
    path = pathlib.Path(patch)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 20000:
        return {"decision": "STOP", "reason": "invalid_patch"}
    data = path.read_bytes()
    expected = ("diff --git a/" + TARGET + " b/" + TARGET).encode()
    if not data.startswith(expected + b"\n"):
        return {"decision": "STOP", "reason": "unexpected_patch_header"}
    if data.count(b"diff --git ") != 1 or b"new file mode 100644" not in data:
        return {"decision": "STOP", "reason": "unexpected_patch_scope"}
    return {"decision": "READY_FOR_PROTECTED_PUBLISHER",
            "repository": REPO, "issue": ISSUE, "base": base_sha,
            "branch": BRANCH, "target": TARGET, "draft": True,
            "title": "docs: OpenHands Issue #220 proof"}


def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        path = pathlib.Path(temp) / "proof.patch"
        path.write_bytes(("diff --git a/" + TARGET + " b/" + TARGET +
                          "\nnew file mode 100644\n--- /dev/null\n+++ b/" +
                          TARGET + "\n@@ -0,0 +1 @@\n+proof\n").encode())
        base = "a" * 40
        assert plan(path, base)["decision"] == "STOP"
        assert plan(path, base, approved=True, lease=True, budget=True,
                    writer=True, collision_clear=True)["decision"] == "READY_FOR_PROTECTED_PUBLISHER"
        path.write_bytes(path.read_bytes() + b"diff --git a/package.json b/package.json\n")
        assert plan(path, base, approved=True, lease=True, budget=True,
                    writer=True, collision_clear=True)["decision"] == "STOP"
    print("PASS: draft handoff rejects missing gates and multi-file patches")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("only offline --self-test is exposed; no publish CLI")
    self_test()


if __name__ == "__main__":
    sys.exit(main())
