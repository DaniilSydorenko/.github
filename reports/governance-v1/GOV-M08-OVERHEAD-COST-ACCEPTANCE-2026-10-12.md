# Governance v1 — Overhead & Cost Acceptance

Date: 2026-10-12
Status: PASS for the current design
Scope: Governance v1 architecture and maintenance overhead

## Acceptance question

Does Governance v1 make engineering faster, safer and easier to manage without becoming a separate governance product?

Current answer: **yes**, provided the stop-building boundary remains enforced.

## Current governance footprint

Governance v1 currently adds or relies on:

- one central discovery registry: `governance/repository-registry.json`;
- one structural validator: `grs/validate_repository_registry.py`;
- one read-only on-demand live drift auditor: `grs/audit_repository_registry_drift.py`;
- deterministic unit tests under the existing `grs/tests` suite;
- the existing GRS Control Plane workflow.

It does **not** add:

- a database;
- a dashboard;
- a service;
- a GitHub App;
- a new scheduler;
- a recurring governance worker;
- a universal agent framework;
- a duplicate roadmap;
- a duplicate live-status store;
- an Issue-per-change process.

## Runtime / CI cost

Normal GRS CI remains one existing workflow and one Python unittest suite.

The live seven-repository drift audit is deliberately **on demand**, not a network call on every ordinary PR. This avoids:

- cross-repository token distribution to normal CI;
- network-induced false failures;
- repeated private-repository API reads;
- a new recurring workflow;
- unnecessary Actions minutes.

The auditor itself is regression-tested with deterministic mocked responses inside the existing suite.

## Coordination cost

The registry removes repeated discovery work by answering:

- repository;
- canonical default branch;
- domain owner;
- GRS class;
- roadmap pointer;
- agent/authority/governance pointers;
- specialized tracker roles.

It intentionally does not answer mutable task completion. That remains local to the owning repository.

Roadmap, Issues and PRs remain separate:

- roadmap = milestones/priorities;
- Issue = independently actionable defect/blocker/work item when useful;
- PR = implementation/evidence;
- report = read-only reconciliation.

## Failure behavior

The live drift auditor fails closed:

- unreadable private repository = operational error, not false drift and not false green;
- API failure = operational error;
- branch mismatch = drift;
- missing declared pointer after repository access succeeds = drift;
- no token = refuse authoritative audit.

No repair is automatic. Detection and repair remain separate authorization steps.

## Maintenance acceptance

The current model is acceptable because each added surface has a distinct job:

1. registry — discovery index;
2. structural validator — local deterministic contract;
3. drift auditor — optional live verification;
4. existing GRS workflow — regression safety.

Adding another registry, status database, dashboard, scheduled governance checker or copied repository policy would currently add more maintenance than verified value and should be rejected or deferred.

## Stop-building consequence

After contract acceptance and the remaining read-only validation acceptance are complete, Governance v1 should freeze.

Future governance infrastructure requires evidence of a recurring failure that cannot be solved by the existing registry + GRS + local repository authority model.

## Result

**PASS — current Governance v1 overhead is bounded and proportionate to verified value.**
