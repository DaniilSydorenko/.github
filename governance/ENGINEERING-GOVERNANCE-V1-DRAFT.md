# Engineering Governance v1 — Minimal Contract (owner-decision draft)

**Status:** DRAFT / NON-ENFORCING. **Owner:** GitHub HQ. **Scope:** seven repositories in [repository-registry.json](repository-registry.json). **Decision:** [issue #56](https://github.com/DaniilSydorenko/.github/issues/56).

This file **does not** create a second governing authority, mandatory seven-repository CI, universal agent framework, product acceptance, release/publishing rights, or scheduler permission. It summarizes accepted boundaries and isolates the one outstanding enforcement decision. The former verbose draft remains recoverable from Git history.

## Simplicity & Speed Directive — already approved

- **Reuse before build.** Existing GRS, local CI, repository registry, and Control Plane are the infrastructure. No new database, service, dashboard, scheduler, agent or standing manual review without a proven defect.
- **One status owner.** Repository-local roadmaps own priorities; Issues own actionable decisions/defects; PRs and exact-head CI prove proposed changes; accepted default branches prove integration; external providers prove runtime state. No mirrored progress databases.
- **Discovery, not forced layout.** Registry pointers locate local authority. Existing local trackers, file names and release flows stay domain-owned.
- **Consequence-based gates.** Normal authorized Class A/B paths should be fast; Class C, credentials, publication/visibility, history rewrite, stable releases, and owner/security approvals remain gated.
- **Stop building.** After evidenced infrastructure acceptance, freeze this program. Documentation, drafts and green PR CI alone do not earn acceptance.

## C01–C07 — compact contract and disposition

| ID | Existing baseline (keep) | New mandatory enforcement |
| --- | --- | --- |
| **C01 — Source of Truth** | Git default branch, per-domain roadmap/data authority, pointer registry; scheduler/provider owns live execution truth | **NOT APPROVED**: requiring new machine-verifiable local metadata |
| **C02 — Roadmap Integrity** | Existing stable milestones, owner-controlled edits, Git history and evidence-backed status | **NOT APPROVED**: cross-repo task/roadmap gate |
| **C03 — Agent Execution** | Existing default-deny merge policy, bounded worker permissions, exact-head/CI/collision/owner gates | **NOT APPROVED**: mandatory worker policy-consumption instrumentation |
| **C04 — Evidence & Completion** | `planned → implemented → tested → merged → deployed → released → runtime-verified` as advisory vocabulary; local exit gates prevail | **NOT APPROVED**: uniform required lifecycle gate |
| **C05 — Cross-Repository Authority** | HQ owns GRS and portfolio discovery; Control Plane owns fleet/runtime; domains own products, releases, source data and PRs | **NOT APPROVED**: new centralized product-control checks |
| **C06 — Security, Reliability & Cost** | GRS, secret scan, local security/CI, owner approval, least privilege and bounded retries | **NOT APPROVED**: forced all-repo equivalence/adoption gate |
| **C07 — Reconciliation & Reporting** | Read-only drift auditor, existing fleet evidence reporter, canonical local status and truthful UNKNOWN | **NOT APPROVED**: recurring compulsory reporting/enforcement |

**Control categories:** Existing required controls stay required *where already installed and authorized*. Existing advisory discovery and on-demand read-only validators remain advisory. Proposed binding C01–C07 changes remain blocked by #56; absence of approval is not a reason to disable existing security.

## Canonical authority and exceptions

- HQ: [GRS](../grs/OPERATING-MODEL.md), [HQ boundaries](../reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md), [default-deny merge policy](autopilot-merge-policy.json), [round protocol](../reports/github-hq/ENGINEERING-ROUND-PROTOCOL.md).
- Control Plane: its own `AUTHORITY.md`, `CONTROL_PLANE.md`, scheduler and telemetry contracts. Synchronous HQ does **not** inherit scheduled worker merge authority.
- Domains: LADVERO/ListingKit, Career Intelligence (private career-data authority), Handbook, Labs and Haversine retain code/content/release/roadmap decisions.
- Private repositories do not automatically require public OSS assets; Haversine retains `master`, OSS/release gates and package-specific CI. Archived repositories are read-only by default. The profile repository is outside the seven-repo scope.
- GRS pilot/discovery coverage **does not equal** seven-repository manifest enforcement or publication safety; missing evidence is **UNKNOWN**, and a tracked private path requires independent publication review.

## Explicit decision and exit gates

**Issue #56:** Owner may (A) approve a precisely bounded mandatory subset with explicit exceptions, (B) reject new cross-repo enforcement and accept existing GRS/discovery as sufficient, or (C) defer. **Recommended lean disposition: B**, unless live operational evidence proves an unaddressed recurring safety gap. This draft is **not** that owner decision.

**GOV-M07 operational proof:** Run existing reporter against observed seven-repo discovery, manifest, class, CI and operational evidence; record PASS/FAIL/UNKNOWN/approved EXCEPTION and provenance. An all-UNKNOWN smoke test proves only reporter mechanics. Do not require domain PR completion.

**GOV-M08 acceptance & freeze:** Reconcile #56, true seven-repo evidence, three completed bounded engineering rounds, independent security/visibility gates (including [PR #82](https://github.com/DaniilSydorenko/.github/pull/82)), and actual operational overhead. Acceptance requires owner authorization and applicable CI, not extra governance documents.

## Conflict order

Safety/owner gates → explicit domain authority → active central GRS → local rules → worker prompt → chat memory. Local policy can tighten but cannot silently weaken a higher safety boundary. No change to M4 scope without a separate owner decision.
