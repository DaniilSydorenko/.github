#!/usr/bin/env python3
"""Offline sequential issue runner simulation. Never starts an LLM or writes to GitHub.

Two deterministic mock issues demonstrate queue advancement after a verified
result, and fail-closed behavior on unsafe output or execution failure.
"""
import dataclasses


@dataclasses.dataclass(frozen=True)
class Task:
    issue: int
    target: str


@dataclasses.dataclass(frozen=True)
class Outcome:
    issue: int
    status: str
    detail: str


def run_queue(tasks, *, execute, verify, authority, max_tasks=2):
    if authority is not _OFFLINE_TEST_AUTHORITY:
        raise PermissionError("offline simulation authority required")
    if not 1 <= max_tasks <= 2:
        raise ValueError("simulation capped at two tasks")
    if len(tasks) > max_tasks:
        raise ValueError("task queue exceeds simulation cap")
    if len({t.issue for t in tasks}) != len(tasks):
        raise ValueError("duplicate issues")
    results = []
    for task in tasks:
        try:
            execution = execute(task)
            if execution != "completed":
                results.append(Outcome(task.issue, "STOP", "executor_failed"))
                break
            if verify(task) is not True:
                results.append(Outcome(task.issue, "STOP", "artifact_not_verified"))
                break
            results.append(Outcome(task.issue, "PASS", "verified_offline"))
        except Exception:
            results.append(Outcome(task.issue, "STOP", "execution_or_verification_error"))
            break
    return results


_OFFLINE_TEST_AUTHORITY = object()


def self_test():
    tasks = [Task(220, "docs/agent-pilot-proof.md"),
             Task(221, "docs/second-simulation-proof.md")]
    events = []
    def execute(task):
        events.append(("execute", task.issue))
        return "completed"
    def verify(task):
        events.append(("verify", task.issue))
        return True
    try:
        run_queue(tasks, execute=execute, verify=verify, authority=None)
    except PermissionError:
        pass
    else:
        raise AssertionError("untrusted simulation accepted")
    assert events == []
    outcome = run_queue(tasks, execute=execute, verify=verify,
                        authority=_OFFLINE_TEST_AUTHORITY)
    assert [o.status for o in outcome] == ["PASS", "PASS"]
    assert events == [("execute", 220), ("verify", 220),
                      ("execute", 221), ("verify", 221)]
    events.clear()
    outcome = run_queue(tasks, execute=execute,
                        verify=lambda task: task.issue != 220,
                        authority=_OFFLINE_TEST_AUTHORITY)
    assert len(outcome) == 1 and outcome[0].status == "STOP"
    assert events == [("execute", 220)]
    events.clear()
    outcome = run_queue(tasks, execute=lambda task: "failed",
                        verify=verify, authority=_OFFLINE_TEST_AUTHORITY)
    assert len(outcome) == 1 and outcome[0].detail == "executor_failed"
    assert events == []
    try:
        run_queue(tasks + [Task(222, "docs/third.md")],
                  execute=execute, verify=verify,
                  authority=_OFFLINE_TEST_AUTHORITY)
    except ValueError:
        pass
    else:
        raise AssertionError("unbounded queue accepted")
    print("PASS: offline sequential queue advances 220->221, stops on failure, capped at two")


if __name__ == "__main__":
    self_test()
