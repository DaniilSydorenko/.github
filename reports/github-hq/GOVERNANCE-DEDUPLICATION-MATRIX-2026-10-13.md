# Governance documentation / workflow deduplication matrix — 2026-10-13

**Scope:** bounded evidence and remediation under existing GOV-M07/M08. No new roadmap, no new governance project, no product-roadmap copies, no deletion. Status: PROPOSED in HQ PR #79, not accepted default-branch truth.

**Classification:** CD confirmed duplicate; CA conflicting authority; LS legitimate local specialization; HA historical artifact; UV unverified. A textual overlap alone is not a confirmed duplicate.

| ID | Repository / path | Role | Canonical owner | Classification / observed overlap | Risk | Action | Owner approval? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DOC-01a | `listing-kit/.autopilot/worker-policy.md` | Scheduled Ladvero worker scope and execution roadmap | Ladvero worker / Control Plane execution; `.github` global engineering | **CA**: line 3 calls Control Plane 'canonical global governance'; line 33 assigns `docs/maintenance/LADVERO_ROADMAP.md` worker execution | Medium: global vs worker authority ambiguity | **LINK**: clarify two distinct scopes in domain-owned PR; preserve worker owner gates | Domain owner for local edit; #56 for new binding semantics |
| DOC-01b | `career-intelligence/.autopilot/worker-policy.md` | Scheduled Career worker policy | Career worker / Control Plane execution; `.github` global engineering | **CA**: line 3 same global-governance wording | Medium | **LINK**: clarify authority, no worker privilege expansion | Domain owner; #56 for enforcement |
| DOC-02 | `.github/governance/repository-registry.json` Handbook `discovery.roadmap=handbook/00-canonical-toc.md` | Discovery pointer | HQ discovery; Handbook content authority | **CA/UV**: TOC is canonical coverage/scope, not demonstrated execution status | Medium: misdirects agents | **INVESTIGATE** true execution status path, then adjust role metadata/pointer; avoid inventing roadmap | HQ metadata review + Handbook owner |
| DOC-03a | `engineering-handbook/automation/ARCHITECTURE.md` | Local automation architecture | Handbook | **LS**: references `HANDBOOK_OPERATING_SYSTEM.md` as constitutional authority | Low | **KEEP**; relative path needs context check | No unless changed |
| DOC-03b | `engineering-handbook/automation/handbook-status.json` | Machine-readable checkpoint | Handbook | **LS**: `governance: HANDBOOK_OPERATING_SYSTEM.md`, `canonical_scope: handbook/00-canonical-toc.md`, personalized roadmap `daniil/learning-roadmap.md` | Low | **KEEP**; distinguish checkpoint from execution status and TOC | No unless changed |
| DOC-03c | `engineering-handbook/HANDBOOK_OPERATING_SYSTEM.md` | Canonical local constitution | Handbook | **LS / VERIFIED EXISTS at repo root**; no missing-file defect | Low | **KEEP**; do not create duplicate | No |
| DOC-04a | `listing-kit/ROADMAP.md` and `TASKS.md` | Product strategic roadmap / task execution (roles require line-level confirmation) | Ladvero | **UV** overlap with maintenance roadmap, MVP readiness and detailed plans | Medium: status duplication | **INVESTIGATE** mutable-status owners; LINK only where confirmed | Ladvero |
| DOC-04b | `listing-kit/docs/maintenance/LADVERO_ROADMAP.md` | Worker execution/maintenance roadmap; explicitly canonical for this scope | Ladvero Autopilot | **LS** separate from product roadmap; reports 59% within its own scope | Medium if misread as product total | **KEEP/LINK** with explicit scope label | Ladvero |
| DOC-04c | `listing-kit/docs/mvp/MVP_READINESS.md` | Product release gate | Ladvero | **LS / UV** overlapping status not fully compared | Medium | **KEEP** gate; avoid copying execution status | Ladvero |
| DOC-05 | `career-intelligence/docs/PLATFORM_ROADMAP_V2.md`, `roadmap.md`, `docs/PUBLIC_V2_DEEP_AUDIT_ROADMAP_2026-10-11.md`, `docs/ASSISTANT_PLATFORM_ROADMAP.md` | Platform, public, assistant bounded workstreams | Career Intelligence respective domain owners | **LS**: PLATFORM explicitly states separate from Autopilot; 88% is PLATFORM-only | Medium if merged into false universal % | **KEEP/LINK** parent/child and measurement scope, no new aggregate | Career owners |
| DOC-06 | `haversine-geolocation/.github/workflows/grs.yml` | Local GRS CI consumer | Haversine; shared validator from `.github` | **CA**: central GRS checkout `ref: main` floating; checkout credential minimization not explicit | Medium: reproducibility | **INVESTIGATE** pinned-version/rollback design, then domain PR | Haversine; #56 if enforcing new rules |
| DOC-07a | `.github/.github/workflows/grs-control-plane.yml` | Central policy regression | HQ | **LS**: read-only; SHA-pinned checkout; PR path filters exclude `reports/**` | Low; audit-only PR gets no GRS run | **KEEP**; don't claim green CI without run | HQ |
| DOC-07b | `autopilot-control-plane/.github/workflows/{issue-sync,reconcile,roadmap-executor,weekly-review}.yml` | Scheduler worker execution and telemetry | Control Plane | **UV** authenticated checkout in write jobs may be necessary | Medium if blindly changed | **INVESTIGATE** auth before modifying | Control Plane |
| DOC-07c | `listing-kit/.github/workflows/ci.yml` | Product CI | Ladvero | **LS** product build; build checkout lacks explicit `persist-credentials: false` | Low/medium | **KEEP** product CI, investigate credential requirement | Ladvero |
| DOC-07d | `listing-kit/.github/workflows/secret-scan.yml`, `haversine-geolocation/.github/workflows/secret-scan.yml` | Secret scans | Each domain, central security contract | **LS** similar SHA-pinned Gitleaks with full checkout, weekly schedule; not proof of full-history pass | Medium if overstated | **KEEP** local event gates; separately verify scan execution | Domain |
| DOC-07e | `autopilot-control-plane`, Career, Handbook, Labs `.github/workflows/autopilot-help.yml` | Reusable central health caller | Local runtime authority / central reusable implementation | **LS** `@main` mutable shared dependency | Medium | **LINK/INVESTIGATE** versioning, rollout and rollback | HQ + local owners |

## Confirmed outcomes and non-findings

- **No verified byte-identical redundant documents** were established; do not label anything CD or delete.
- Handbook operating constitution **exists at repository root**. The root references are not missing-file defects; verify relative links only where tooling actually interprets them.
- `handbook/00-canonical-toc.md` is a coverage inventory, not proven execution roadmap. Do not silently substitute `daniil/learning-roadmap.md`, which is personalized learning.
- Existing seven-repo discovery coverage is not local GRS conformance (1/7 manifests observed).
- Shared workflow `@main` is a real mutable dependency; versioning changes need deliberate update/recovery policy.
- No branch, repo, document or workflow was deleted.

## Bounded remediation and stop rule

1. HQ: correct discovery role semantics **only after** verifying Handbook execution authority. Avoid second mutable tracker.
2. Domain owners: two small wording-only worker policy PRs (DOC-01), preserving scheduled execution authority and owner gates.
3. HQ/domain: versioning and minimal permissions plan for shared GRS/health workflows; pilot Haversine under its owner.
4. Domain owners: link role/scope descriptions in Ladvero and Career roadmaps only if real mutable-status collisions are confirmed.
5. GOV-M07: machine-readable read-only conformance evidence; GOV-M08: owner #56 decision, one full Haversine cycle and freeze.

**Stop auditing** once a future worker can reproduce answers to: global rule path, worker execution policy path, domain roadmap path, enforcing workflow path, and conflict-resolution authority. No repeat audits on unchanged SHAs.

**Unknown:** complete YAML semantics for all seven repos, live branch protection/rulesets, actual scheduler policy-loading, required exact-head checks, all mutable status overlaps, and historical scan outcomes.
