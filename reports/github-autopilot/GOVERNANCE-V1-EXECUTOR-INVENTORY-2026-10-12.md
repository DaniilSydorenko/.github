# GitHub Autopilot — Governance v1 Executor Inventory

Date: 2026-10-12
Status: **AUTO-GOV-01 COMPLETE / AUTO-GOV-02 PROPOSAL ONLY**

This document is the GitHub Autopilot executor view. It does not approve the proposed C01–C07 contract, change cross-repository authority, or replace the [CAREER][GITHUB] HQ roadmap.

## Canonical mechanisms already available

| Proposed target | Existing canonical capability | Executor assessment |
| --- | --- | --- |
| C01 — repository / roadmap discovery and authority metadata | GRS repository manifests + schema; `grs/OPERATING-MODEL.md`; HQ/Autopilot boundary contract; repository-local `AGENTS.md` / governance entrypoints where present | **PARTIAL** — repository class/visibility/maturity exist; roadmap and local-authority discovery are not uniform across all seven repos |
| C02 — roadmap integrity and defect traceability | HQ `[NEW]` rule; Control Plane fixed-roadmap / no-moving-goal rules; GRS policy drift checks; GitHub Issues/PR evidence | **PARTIAL** — no shared machine-verifiable roadmap-reference contract |
| C03 — bounded task contract validation | default-deny Autopilot merge policy; exact-head/live-state/collision rules; Control Plane authority hierarchy; repository-local worker rules | **PARTIAL/STRONG** — execution boundaries exist, but there is no accepted generic task-contract schema |
| C04 — completion evidence and acceptance | exact-head CI; merge-policy gates; GRS checks; release/runtime evidence kept distinct in existing repositories | **PARTIAL/STRONG** — evidence practice exists; shared completion-stage vocabulary is not accepted policy yet |
| C05 — cross-repository ownership | HQ/Autopilot boundary contract; Control Plane `AUTHORITY.md`; domain-local ownership docs | **PARTIAL/STRONG** — rules exist but are distributed; no accepted central machine-readable seven-repo authority registry |
| C06 — security / reliability / cost safeguards | GRS; secret scans; least privilege; default-deny merge policy; retry-churn suppression; Control Plane Lean/stop-building rules | **STRONG** — cost/budget declarations are not uniformly machine-verifiable and should not be added without an approved contract |
| C07 — read-only reconciliation / truthful reporting | `grs/check_policy_drift.py`; repository audit; publication-history audit; reusable Autopilot health; live GitHub evidence | **STRONG/PARTIAL** — reconciliation exists by domain, but no accepted shared registry reconciliation contract |

## Reusable implementation surfaces

Use before adding anything new:

- `grs/repository.schema.json`
- `grs/validator.py`
- `grs/classes/profiles.json`
- `grs/audit_repository.py`
- `grs/check_policy_drift.py`
- `grs/publication/*`
- `governance/autopilot-merge-policy.json`
- `grs/validate_autopilot_merge_policy.py`
- `.github/workflows/grs-control-plane.yml`
- `.github/workflows/reusable-autopilot-health.yml`
- `reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md`
- Control Plane `CONTROL_PLANE.md`, `SAFETY.md`, `AUTHORITY.md`

No new service, database, runner, scheduler or parallel validator stack is justified by the current inventory.

## Repository discovery gaps observed

- ListingKit has a strong root `AGENTS.md`, but uses multiple planning surfaces whose roles must remain locally defined.
- Career Intelligence root `AGENTS.md` currently protects Lovable history but is not a complete engineering discovery entrypoint.
- Engineering Handbook has no root `AGENTS.md`; its canonical operating contract is `HANDBOOK_OPERATING_SYSTEM.md`.
- Engineering Labs has a strong root `AGENTS.md`.
- Haversine has strong contribution/release/roadmap surfaces but no root `AGENTS.md`.
- Control Plane has explicit authority and safety contracts.
- Central `.github` already owns GRS and HQ/Autopilot boundaries.

These are discovery inconsistencies, not permission for GitHub Autopilot to edit product roadmaps.

## Minimal validator delta — proposal only

Until [CAREER][GITHUB] approves the actual Governance v1 specification, do **not** introduce C01–C07 as enforcement policy.

The smallest likely delta after approval is:

1. extend an existing GRS machine-readable surface rather than create a parallel schema stack;
2. encode stable discovery pointers and authority metadata only;
3. never copy progress percentages or live task state into a central registry;
4. add deterministic negative tests for malformed/duplicate/unauthorized metadata;
5. reuse GRS Control Plane for exact-head validation;
6. add read-only reconciliation only after the pilot proves the metadata useful.

Cross-repository write authority, scheduler authority, product-roadmap authority, visibility, releases and evidence semantics remain unchanged.

## Pilot result

The Haversine pilot is now complete through the owning lane and HQ reconciliation:

- Issue #149 supplied stable task identity;
- PR #150 implemented the Biome quality gate with exact-head CI/security evidence;
- PR #151 reconciled the accepted local roadmap and CHANGELOG baseline;
- HQ PR #58 recorded GOV-M05 completion without transferring product ownership to central governance.

This is sufficient pilot evidence. Do not create a second pilot merely to generate more governance activity.

## Lean implementation audit

A fresh review against the owner lean directive found:

- no justification for a second governance database, runner, scheduler, dashboard or control plane;
- no justification for a parallel generic validator stack: existing GRS + its domain-specific publication validator already provide the correct extension points;
- existing documentation is sufficient to define the operating model; new documentation should be exceptional and problem-driven;
- the main remaining Governance v1 value is executable validation/discovery after contract approval, not additional architecture prose;
- read-only reconciliation is already the correct default and should remain separate from repairs.

Overhead rule: prefer one reusable check in the existing GRS Control Plane over repository-by-repository bespoke automation. If a proposed rule cannot demonstrate a material safety/correctness/discovery benefit, do not implement it.

## Stop conditions

Stop implementation and require policy approval when a proposed change would:

- introduce a new authority field whose semantics are not approved;
- require product-roadmap changes;
- mutate another worker's roadmap;
- alter scheduler/runtime authority;
- create a second status store;
- create a new recurring workflow;
- broaden merge/write authority.

Independent existing GRS maintenance may continue normally.
