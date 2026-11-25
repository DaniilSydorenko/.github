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
    print("PASS: quality result contract")

if __name__ == "__main__":
    self_test()
