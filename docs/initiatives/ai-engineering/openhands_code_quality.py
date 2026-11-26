"""Offline quality-result contract. No model, credentials or publication authority."""
from dataclasses import dataclass

COMMANDS = ("typecheck", "test", "build", "quality")

@dataclass(frozen=True)
class CheckResult:
    name: str
    exit_code: int
    timed_out: bool = False

def verify_quality(results):
    """Reject missing, duplicate, reordered, failed or timed-out checks."""
    results = tuple(results)
    if len(results) != len(COMMANDS):
        return False
    return all(
        isinstance(result, CheckResult)
        and result.name == expected
        and type(result.exit_code) is int
        and result.exit_code == 0
        and result.timed_out is False
        for expected, result in zip(COMMANDS, results)
    )

def run_quality(workspace, *, image):
    """Run candidate checks in a disposable, network-disabled container.

    The caller must provision a trusted dependency image with /opt/target/node_modules.
    No host environment, Docker socket, credentials or writable host mounts are passed.
    """
    import pathlib
    import subprocess
    import re
    root = pathlib.Path(workspace).resolve(strict=True)
    if not root.is_dir() or not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise ValueError("invalid_quality_workspace_or_image")
    results = []
    for name in COMMANDS:
        command = [
            "docker", "run", "--rm", "--pull=never", "--network=none",
            "--cap-drop=ALL", "--security-opt=no-new-privileges",
            "--user=1000:1000", "--read-only", "--pids-limit=256",
            "--memory=2g", "--cpus=2", "--tmpfs=/tmp:rw,exec,size=1g",
            "--mount", f"type=bind,source={root},target=/candidate,readonly",
            "--entrypoint=/bin/sh", image, "-ec",
            'mkdir /tmp/work && cp -R /candidate/. /tmp/work/ && cd /tmp/work && '
            'ln -s /opt/target/node_modules node_modules && HOME=/tmp npm run "$1"',
            "quality", name,
        ]
        try:
            completed = subprocess.run(command, timeout=180, check=False,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            results.append(CheckResult(name, completed.returncode))
        except subprocess.TimeoutExpired:
            results.append(CheckResult(name, 1, True))
        except OSError:
            results.append(CheckResult(name, 1))
        if results[-1].exit_code != 0 or results[-1].timed_out:
            break
    return tuple(results)

def require_quality(workspace, *, image):
    from openhands_164_patch_contract import PatchContractError
    results = run_quality(workspace, image=image)
    if not verify_quality(results):
        failed = next((r.name for r in results if r.exit_code or r.timed_out), "incomplete")
        raise PatchContractError("quality_gate_failed:" + failed)

def self_test():
    good = tuple(CheckResult(name, 0) for name in COMMANDS)
    assert verify_quality(good)
    assert not verify_quality(())
    assert not verify_quality(good[:-1])
    assert not verify_quality(good[::-1])
    assert not verify_quality(good[:-1] + (good[0],))
    for index, name in enumerate(COMMANDS):
        for bad in (CheckResult(name, 1), CheckResult(name, 0, True),
                    CheckResult(name, False)):
            assert not verify_quality(good[:index] + (bad,) + good[index+1:])
    from unittest.mock import patch
    import tempfile
    import subprocess
    with tempfile.TemporaryDirectory() as root:
        image = "sha256:" + "a" * 64
        with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
            assert verify_quality(run_quality(root, image=image))
            assert run.call_count == 4
            for call in run.call_args_list:
                args = call.args[0]
                assert "--network=none" in args and "--pull=never" in args
                assert "--read-only" in args and "--cap-drop=ALL" in args
                assert any("target=/candidate,readonly" in arg for arg in args)
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 180)):
            assert not verify_quality(run_quality(root, image=image))
        with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1)) as run:
            assert not verify_quality(run_quality(root, image=image))
            assert run.call_count == 1
            from openhands_164_patch_contract import PatchContractError
            try:
                require_quality(root, image=image)
            except PatchContractError:
                pass
            else:
                raise AssertionError("failed quality gate accepted")
    print("PASS: quality result contract and isolated runner fixtures")

if __name__ == "__main__":
    self_test()
