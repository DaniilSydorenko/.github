"""Offline Hello World V2 event bridge — SIMULATION ONLY / NOT PRODUCTION AUTHORITY.

Reacts to synthetic accept events and invokes the existing stubbed single-Issue
dispatcher. No network, GitHub writes, workflow wiring, or production scheduler.

This is not authenticated GitHub webhook processing: ``SyntheticAcceptEvent`` and
local handoff snapshots are untrusted inputs re-checked against in-memory fixtures.
In-process ``_processed_accept_ids`` is replay suppression for unit tests only,
not durable cross-process idempotency. No automatic merge or live dispatch is permitted by this module.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable

from execution_outcome import verify_execution
from github_ref_lease import Controller, LeaseError
from managed_cursor_launch import launch_single_approved_issue
from sequential_handoff import preview_next_after_merge
from test_managed_cursor_issue_launch import approved_handoff, snapshot
from test_managed_cursor_launch import permit as base_permit
from test_preview_one import fixture

REPO = "example/test"
A, B, C = "a" * 40, "b" * 40, "c" * 40
PATH = "src/feature.py"

KNOWN_ACCEPT_EVENTS = frozenset({"PR_A_ACCEPTED"})


@dataclass(frozen=True)
class SyntheticAcceptEvent:
    """Untrusted synthetic webhook payload — verified only inside simulation guards."""

    kind: str
    event_id: str
    pr_number: int
    head_sha: str
    merge_sha: str
    owner_accepted: bool
    ci_conclusion: str = "success"


def handoff_after_issue_a_accepted() -> dict[str, Any]:
    """Post–Issue-42-accept handoff snapshot for preview_next_after_merge."""
    data = snapshot()
    task = {
        "number": 43,
        "order": 3,
        "state": "open",
        "accepted": False,
        "owner_approved": True,
        "owner_gate": False,
        "scope": "ui_low_risk",
        "allowed_paths": [PATH],
        "dependencies": [{"number": 42, "status": "accepted"}],
    }
    data["handoff"]["previous"].update(
        pr_number=312,
        head_sha=B,
        merge_sha=C,
        merge_on_default_verified=True,
        ci="SUCCESS",
        secret_scan="SUCCESS",
        owner_visual_acceptance="accepted",
    )
    data["handoff"]["queue"][1].update(state="closed", accepted=True)
    data["handoff"]["queue"].append(task)
    scoped = data["preview"]
    scoped["collector"]["observed_facts"]["issue_number"] = 43
    scoped["observed"]["issue_number"] = 43
    scoped["semantic"]["issue_number"] = 43
    scoped["semantic"]["issue_url"] = f"https://github.com/{REPO}/issues/43"
    scoped["task"]["issue"] = f"https://github.com/{REPO}/issues/43"
    return data


def accepted_evidence(
    store_state: dict[str, Any],
    *,
    issue_number: int,
    pr_number: int,
    result: dict[str, Any],
    ci: str = "success",
    accepted: bool = True,
) -> dict[str, Any]:
    url = f"https://github.com/{REPO}/pull/{pr_number}"
    return {
        "schema_version": 1,
        "task": {
            "repository": REPO,
            "issue_number": issue_number,
            "pr_number": pr_number,
            "pr_url": url,
            "request_id": store_state["request_id"],
            "owner_authority": "verified",
            "scope_authority": "verified",
            "allowed_paths": [PATH],
            "required_checks": ["CI", "Secret Scan"],
        },
        "lease": {**deepcopy(store_state), "observed_revision": store_state["revision"]},
        "provider": {
            "agent_id": result["agent_id"],
            "run_id": result["run_id"],
            "run": {
                "id": result["run_id"],
                "agentId": result["agent_id"],
                "status": "FINISHED",
            },
            "observation_complete": True,
            "other_active_run": False,
        },
        "pr": {
            "number": pr_number,
            "url": url,
            "state": "closed",
            "merged": True,
            "head_sha": B,
            "observed_head_sha": B,
            "base_sha": A,
            "observed_base_sha": A,
            "merge_sha": C,
            "merged_into_default_proven": True,
            "changed_paths": [PATH],
            "changed_paths_complete": True,
        },
        "checks": [
            {"name": "CI", "head_sha": B, "conclusion": ci, "observed": True},
            {"name": "Secret Scan", "head_sha": B, "conclusion": "success", "observed": True},
        ],
        "attempts": {
            "initial_run_verified": True,
            "corrections": [],
            "failure_evidence_verified": False,
        },
        "acceptance": {
            "issue_criteria": "accepted" if accepted else "pending",
            "owner_merge": "approved",
            "deployment": "not_required",
            "device": "not_required",
        },
    }


def _permit_for_handoff(bundle: dict[str, Any]) -> dict[str, Any]:
    recommendation = preview_next_after_merge(bundle["handoff"])
    rid = recommendation["proposed_request_id"]
    return base_permit(
        request_id=rid,
        proposed_request_id=rid,
        repository=REPO,
        issue_number=recommendation["next_issue_number"],
        head_sha=A,
        pr_number=None,
    )


class HelloWorldEventSimulator:
    """In-memory two-Issue cycle with one PR_A_ACCEPTED → next-Issue bridge."""

    def __init__(
        self,
        *,
        controller: Controller,
        cursor_reader: Any,
        cursor_create: Any,
        bundle: dict[str, Any] | None = None,
    ):
        self.controller = controller
        self.cursor_reader = cursor_reader
        self.cursor_create = cursor_create
        self.bundle = bundle if bundle is not None else snapshot()
        self.trace: list[str] = []
        self._processed_accept_ids: set[str] = set()
        self._issue_b_dispatched_via_event = False
        self._last_launch: dict[str, Any] | None = None

    def _mark(self, label: str) -> None:
        self.trace.append(label)

    def dispatch_issue(self, bundle: dict[str, Any] | None = None) -> dict[str, Any]:
        data = bundle if bundle is not None else self.bundle
        recommendation = preview_next_after_merge(data["handoff"])
        if recommendation["action"] != "READY_FOR_OWNER_DISPATCH":
            return {"state": "STOP", "reason": recommendation["reason"]}
        rid = recommendation["proposed_request_id"]
        pr = _permit_for_handoff(data)
        pr.update(request_id=rid, proposed_request_id=rid)
        result = launch_single_approved_issue(
            request_id=rid,
            bundle=data,
            permit=pr,
            controller=self.controller,
            cursor_reader=self.cursor_reader,
            cursor_create=self.cursor_create,
        )
        self._last_launch = result
        return result

    def start_issue_a(self) -> dict[str, Any]:
        self._mark("START")
        launched = self.dispatch_issue(self.bundle)
        if launched.get("state") == "STARTED":
            self._mark("PR")
        return launched

    def wait_for_owner_accept(self) -> None:
        self._mark("WAIT_ACCEPT")

    def finalize_issue_a(
        self,
        launched: dict[str, Any],
        *,
        pr_number: int = 312,
        accepted: bool = True,
        ci: str = "success",
    ) -> dict[str, Any]:
        store = self.controller.store
        rid = store.state["request_id"]
        self.controller.transition(rid, "RUNNING", "VERIFYING")
        self.controller.bind_generated_pr(
            rid,
            expected_issue_url=f"https://github.com/{REPO}/issues/42",
            generated_pr_url=f"https://github.com/{REPO}/pull/{pr_number}",
        )
        evidence = accepted_evidence(
            store.state,
            issue_number=42,
            pr_number=pr_number,
            result=launched,
            accepted=accepted,
            ci=ci,
        )
        checked = verify_execution(evidence)
        if checked["status"] == "ACCEPTED_OBSERVED":
            self._mark("ACCEPT")
            self.controller.release_verified(
                rid,
                provider_terminal=True,
                integration_accepted=True,
                manual_approval=True,
            )
            self._mark("LEASE_RELEASE")
            self.bundle = handoff_after_issue_a_accepted()
        return checked

    def handle_pr_a_accepted(self, event: SyntheticAcceptEvent) -> dict[str, Any]:
        """Event-driven bridge: Accept A → dispatch Issue B (stubbed), replay-safe.

        ``event.owner_accepted`` is not owner proof; handoff ``owner_visual_acceptance``
        must already match trusted simulation state. Bounded to Issue #43 only.
        """
        if event.kind not in KNOWN_ACCEPT_EVENTS:
            return {"state": "STOP", "reason": "unknown_event", "trace": list(self.trace)}
        if event.event_id in self._processed_accept_ids:
            return {"state": "IGNORED", "reason": "replay_suppressed", "trace": list(self.trace)}
        if not event.owner_accepted:
            return {"state": "STOP", "reason": "owner_accept_unproven", "trace": list(self.trace)}
        if event.ci_conclusion != "success":
            return {"state": "STOP", "reason": "exact_head_ci_not_green", "trace": list(self.trace)}
        if event.head_sha != B or event.merge_sha != C or event.pr_number != 312:
            return {"state": "STOP", "reason": "stale_or_wrong_sha", "trace": list(self.trace)}

        phase = self.controller.store.state.get("phase")
        if phase != "IDLE":
            return {"state": "BUSY", "reason": "lease_not_released", "trace": list(self.trace)}

        handoff = self.bundle.get("handoff", {})
        previous = handoff.get("previous", {})
        if previous.get("owner_visual_acceptance") != "accepted":
            return {"state": "STOP", "reason": "handoff_not_ready", "trace": list(self.trace)}

        recommendation = preview_next_after_merge(handoff)
        if recommendation["action"] != "READY_FOR_OWNER_DISPATCH":
            return {
                "state": "STOP",
                "reason": "handoff_" + recommendation["reason"],
                "trace": list(self.trace),
            }
        if recommendation["next_issue_number"] != 43:
            return {"state": "STOP", "reason": "unexpected_third_issue", "trace": list(self.trace)}

        launched = self.dispatch_issue(self.bundle)
        self._processed_accept_ids.add(event.event_id)
        if launched.get("state") == "STARTED":
            self._issue_b_dispatched_via_event = True
            self._mark("NEXT")
        return {**launched, "trace": list(self.trace)}

    def finalize_issue_b(self, launched: dict[str, Any], *, pr_number: int = 313) -> dict[str, Any]:
        store = self.controller.store
        rid = store.state["request_id"]
        self.controller.transition(rid, "RUNNING", "VERIFYING")
        self.controller.bind_generated_pr(
            rid,
            expected_issue_url=f"https://github.com/{REPO}/issues/43",
            generated_pr_url=f"https://github.com/{REPO}/pull/{pr_number}",
        )
        evidence = accepted_evidence(
            store.state,
            issue_number=43,
            pr_number=pr_number,
            result=launched,
        )
        checked = verify_execution(evidence)
        if checked["status"] == "ACCEPTED_OBSERVED":
            self._mark("ACCEPT")
            self.controller.release_verified(
                rid,
                provider_terminal=True,
                integration_accepted=True,
                manual_approval=True,
            )
            self._mark("LEASE_RELEASE")
        self._mark("STOP")
        return checked

    @property
    def issue_b_via_event(self) -> bool:
        return self._issue_b_dispatched_via_event
