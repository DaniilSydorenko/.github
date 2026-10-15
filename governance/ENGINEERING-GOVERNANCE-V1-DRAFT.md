# Engineering Governance v1 — Minimal Contract (owner-decision draft)

**Status:** ACTIVE / OWNER-APPROVED LEAN V1 (non-enforcing); 2026-10-15. **Owner:** GitHub HQ. **Scope:** seven repositories in [repository-registry.json](repository-registry.json). **Decision:** [closed issue #56](https://github.com/DaniilSydorenko/.github/issues/56), Option B.

This owner-approved, non-enforcing contract **does not** create a second governing authority, mandatory seven-repository CI, universal agent framework, product acceptance, release/publishing rights, or scheduler permission. It summarizes accepted boundaries and isolates the one outstanding enforcement decision. The former verbose draft remains recoverable from Git history.

## Simplicity & Speed Directive — already approved

- **Reuse before build.** Existing GRS, local CI, repository registry, and Control Plane are the infrastructure. No new database, service, dashboard, scheduler, agent or standing manual review without a proven defect.
- **One status owner.** Repository-local roadmaps own priorities; Issues own actionable decisions/defects; PRs and exact-head CI prove proposed changes; accepted default branches prove integration; external providers prove runtime state. No mirrored progress databases.
- **Discovery, not forced layout.** Registry pointers locate local authority. Existing local trackers, file names and release flows stay domain-owned.
- **Consequence-based gates.** Normal authorized Class A/B paths should be fast; Class C, credentials, publication/visibility, history rewrite, stable releases, and owner/security approvals remain gated.
- **Stop building.** After evidenced infrastructure acceptance, freeze this program. Documentation, drafts and green PR CI alone do not earn acceptance.

## C01–C07 — compact contract and disposition

| ID | Existing baseline (keep) | New mandatory enforcement |
| --- | --- | --- |
| **C01 — Source of Truth** | Git default branch, per-domain roadmap/data authority, pointer registry; scheduler/provider owns live execution truth | **DECLINED by #56**: requiring new machine-verifiable local metadata |
| **C02 — Roadmap Integrity** | Existing stable milestones, owner-controlled edits, Git history and evidence-backed status | **NOT APPROVED**: cross-repo task/roadmap gate |
| **C03 — Agent Execution** | Existing default-deny merge policy, bounded worker permissions, exact-head/CI/collision/owner gates | **NOT APPROVED**: mandatory worker policy-consumption instrumentation |
| **C04 — Evidence & Completion** | `planned → implemented → tested → merged → deployed → released → runtime-verified` as advisory vocabulary; local exit gates prevail | **NOT APPROVED**: uniform required lifecycle gate |
| **C05 — Cross-Repository Authority** | HQ owns GRS and portfolio discovery; Control Plane owns fleet/runtime; domains own products, releases, source data and PRs | **NOT APPROVED**: new centralized product-control checks |
| **C06 — Security, Reliability & Cost** | GRS, secret scan, local security/CI, owner approval, least privilege and bounded retries | **NOT APPROVED**: forced all-repo equivalence/adoption gate |
| **C07 — Reconciliation & Reporting** | Read-only drift auditor, existing fleet evidence reporter, canonical local status and truthful UNKNOWN | **NOT APPROVED**: recurring compulsory reporting/enforcement |

**Control categories:** Existing required controls stay required *where already installed and authorized*. Existing advisory discovery and on-demand read-only validators remain advisory. New binding C01–C07 adoption was expressly declined by the owner in #56, not merely deferred. Only a separately authorized future defect-based decision may reopen it; existing security stays in place.

## Canonical authority and exceptions

- HQ: [GRS](../grs/OPERATING-MODEL.md), [HQ boundaries](../reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md), [default-deny merge policy](autopilot-merge-policy.json), [round protocol](../reports/github-hq/ENGINEERING-ROUND-PROTOCOL.md).
- Control Plane: its own `AUTHORITY.md`, `CONTROL_PLANE.md`, scheduler and telemetry contracts. Synchronous HQ does **not** inherit scheduled worker merge authority.
- Domains: LADVERO/ListingKit, Career Intelligence (private career-data authority), Handbook, Labs and Haversine retain code/content/release/roadmap decisions.
- Private repositories do not automatically require public OSS assets; Haversine retains `master`, OSS/release gates and package-specific CI. Archived repositories are read-only by default. The profile repository is outside the seven-repo scope.
- GRS pilot/discovery coverage **does not equal** seven-repository manifest enforcement or publication safety; missing evidence is **UNKNOWN**, and a tracked private path requires independent publication review.

## Explicit decision and exit gates

**Issue #56 — CLOSED, owner Option B approved 2026-10-15:** no new mandatory cross-repo enforcement. Local manifests, uniform agent files, mandatory CI rollout and worker policy-consumption instrumentation are expressly out of this lean v1 scope. Existing safety/owner gates remain mandatory where already applicable.

**GOV-M07 accepted scope:** existing registry/GRS reporter, read-only drift tests, 35/35 live pointer paths and 7/7 observed default-branch local CI success. Local manifest and new worker-enforcement adoption are owner-declined; unobserved class/runtime proof remains UNKNOWN, never PASS.

**GOV-M08 accepted lean freeze:** owner #56, Haversine pilot, accepted HQ R1/R2, verified seven-repo discovery/local CI and bounded overhead. This is **not** a claim of seven-repo worker/runtime compliance. Branch rulesets remain unverified; publication [PR #82](https://github.com/DaniilSydorenko/.github/pull/82) keeps independent security review. No new GOV tasks merely to eliminate those external UNKNOWNs.

## Conflict order

Safety/owner gates → explicit domain authority → active central GRS → local rules → worker prompt → chat memory. Local policy can tighten but cannot silently weaken a higher safety boundary. No change to M4 scope without a separate owner decision.
