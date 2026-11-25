import tempfile
from pathlib import Path
from openhands_164_patch_contract import _git, PatchContractError
from openhands_code_delivery import collect_changes, publish_changes
from openhands_164_draft_publisher import _PROTECTED_AUTHORITY

def self_test():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _git(root, "init", "-q")
        _git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "base")
        sha = _git(root, "rev-parse", "HEAD").decode().strip()
        paths = ("src/example.ts", "tests/example.test.ts")
        for name in paths:
            file = root / name
            file.parent.mkdir(exist_ok=True)
            file.write_text("export const value = 1;\n")
        changes = collect_changes(root, sha, paths)
        assert set(changes) == set(paths)
        (root / "package.json").write_text("{}")
        try:
            collect_changes(root, sha, paths)
        except PatchContractError:
            pass
        else:
            raise AssertionError("out-of-scope change accepted")
        calls = []
        def fake(method, url, token, payload=None):
            calls.append((method, url, payload))
            if "/git/ref/heads/master" in url: return {"object": {"sha": sha}}
            if "/pulls?" in url: return []
            if method == "GET": return {"tree": {"sha": "a"*40}}
            return {"sha": "b"*40, "html_url": "https://example.invalid/pr"}
        publish_changes(issue=999, base_sha=sha, changes=changes, allowed_paths=paths, token="test", authority=_PROTECTED_AUTHORITY, transport=fake)
        trees = [x[2] for x in calls if x[1].endswith("/git/trees")]
        assert len(trees) == 1 and len(trees[0]["tree"]) == 2
        assert len([x for x in calls if x[0]=="POST" and x[1].endswith("/git/commits")]) == 1
        assert calls[-1][2]["draft"] is True

if __name__ == "__main__":
    self_test()
