# Engineering Governance v1 — Minimal Delta Plan

Date: 2026-10-12
Status: PROPOSED after GOV-M01 / GOV-M02
Principle: extend existing mechanisms; do not build a second management system.

## Do not build

- no new service, database, dashboard or GitHub App;
- no competing engineering roadmap;
- no duplicate repository status store;
- no new recurring worker by default;
- no copied global policy bundle in every repository;
- no product-roadmap changes;
- no scheduler configuration changes.

## GOV-M03 — Governance Contract v1

Draft C01–C07 as a thin contract that references existing GRS, Control Plane and HQ rules. New text should define only missing cross-repository semantics.

Acceptance:
- every contract maps to existing mechanisms;
- every new rule has an identified gap;
- conflicts resolve by named authority;
- proposed authority changes remain separately owner-approved.

## GOV-M04 — Machine-Readable Baseline

Extend existing GRS instead of creating a new schema stack.

Minimal target:
- one central repository registry with repository, default branch, domain owner, repository class and canonical discovery pointers;
- no mutable progress/status percentages in the registry;
- validation reuses the GRS Control Plane.

Acceptance:
- registry is deterministic and schema-valid;
- local truth is referenced, not copied;
- a branch or PR is never mistaken for accepted canonical state.

## GOV-M05 — Pilot

Recommended pilot: **Haversine**.

Why:
- public, bounded OSS repository;
- strong CI and release evidence;
- explicit human roadmap;
- current PR #150 provides a real task/evidence path;
- lower risk of colliding with Ladvero product ownership.

Pilot flow:
discovery → task identity → bounded execution → exact-head checks → merge evidence → roadmap reconciliation.

## GOV-M06 — Seven-Repository Adoption

Roll out only pilot-proven discovery pointers / manifest metadata. Preserve local roadmap shapes.

Priority gaps:
1. Career Intelligence engineering/agent entrypoint beyond Lovable history protection.
2. Engineering Handbook root discovery entrypoint.
3. ListingKit explicit role declaration for `ROADMAP.md`, `TASKS.md`, and `docs/mvp/MVP_READINESS.md`.
4. Central pointers for all seven repositories.

## GOV-M07 — Automated Validation

Reuse `.github/.github/workflows/grs-control-plane.yml`.

Read-only checks only:
- registry schema;
- repository/default-branch declarations;
- required discovery pointer present;
- pointer path syntactically valid;
- no duplicate canonical owner for the same bounded concern.

Do not scrape or store live progress in the registry.

## GOV-M08 — Acceptance & Freeze

Acceptance:
- another authorized agent can discover canonical state for all seven repos without chat memory;
- one pilot task is reproducible from GitHub evidence;
- no authority expansion occurred silently;
- no duplicate status stores exist;
- maintenance overhead is bounded;
- Control Plane Issue #139 and similar runtime defects stay truthfully represented;
- stop-building rule is explicit.

## Dependency map to the existing GitHub roadmap

- M4 — public/private and cross-repository authority boundaries.
- M5 — preferred Haversine pilot evidence.
- M9 — existing GRS policy-as-code and drift-validation foundation.
- M10 — bounded agent execution / Autopilot authority.

The GOV workstream overlays those milestones and must not double-count already completed implementation as new work.
