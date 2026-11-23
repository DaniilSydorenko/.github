#!/usr/bin/env python3
"""Owner-safe CAS lease scope for #164 live runner (fail-closed cleanup)."""
from __future__ import annotations

from dataclasses import dataclass

from github_ref_lease import Controller


@dataclass(frozen=True)
class LeaseCleanupOutcome:
    attempted: bool
    released: bool
    outcome: str | None


class ManagedLeaseSession:
    """Acquire once; release only RESERVED ownership held by this request_id."""

    def __init__(self, lease_store, request_id: str, issue_url: str):
        self.store = lease_store
        self.request_id = request_id
        self.issue_url = issue_url
        self.acquire_outcome: str | None = None
        self._active = False

    def acquire(self) -> str:
        self.acquire_outcome = Controller(self.store).acquire(self.request_id, self.issue_url)
        self._active = self.acquire_outcome in ("ACQUIRED", "ALREADY_OWNED")
        return self.acquire_outcome

    def current_phase(self) -> str | None:
        if not self._active:
            return None
        state = self.store.read().state
        if state.get("request_id") != self.request_id:
            return None
        phase = state.get("phase")
        return phase if isinstance(phase, str) else None

    def release_reserved_if_still_owned(self) -> LeaseCleanupOutcome:
        if not self._active:
            return LeaseCleanupOutcome(False, False, None)
        state = self.store.read().state
        if state.get("request_id") != self.request_id:
            return LeaseCleanupOutcome(True, False, "request_id_mismatch")
        if state.get("phase") != "RESERVED":
            return LeaseCleanupOutcome(True, False, "phase_not_reserved")
        try:
            Controller(self.store).transition(self.request_id, "RESERVED", "IDLE")
            return LeaseCleanupOutcome(True, True, "RELEASED_RESERVED")
        except Exception as exc:
            return LeaseCleanupOutcome(True, False, type(exc).__name__)

    def block_failed_run_if_owned(self) -> LeaseCleanupOutcome:
        if not self._active:
            return LeaseCleanupOutcome(False, False, None)
        state = self.store.read().state
        if state.get("request_id") != self.request_id:
            return LeaseCleanupOutcome(True, False, "request_id_mismatch")
        phase = state.get("phase")
        controller = Controller(self.store)
        try:
            if phase == "RUNNING":
                controller.transition(self.request_id, "RUNNING", "BLOCKED")
                return LeaseCleanupOutcome(True, True, "BLOCKED_RUNNING")
            if phase == "DISPATCHING":
                controller.transition(self.request_id, "DISPATCHING", "BLOCKED")
                return LeaseCleanupOutcome(True, True, "BLOCKED_DISPATCHING")
            if phase == "RESERVED":
                controller.transition(self.request_id, "RESERVED", "IDLE")
                return LeaseCleanupOutcome(True, True, "RELEASED_RESERVED")
        except Exception as exc:
            return LeaseCleanupOutcome(True, False, type(exc).__name__)
        return LeaseCleanupOutcome(True, False, f"phase_{phase}_retained")