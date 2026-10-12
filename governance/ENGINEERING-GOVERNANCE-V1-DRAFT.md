# Engineering Governance v1 — Draft Contract

Status: DRAFT — architecture reconciliation only
Date: 2026-10-12
Owner: [CAREER][GITHUB] HQ

This contract does not create new product authority, scheduler authority, deployment authority, visibility authority, or evidence-promotion authority. It reconciles existing GitHub governance into one discoverable operating model.

## Simplicity & Speed Directive

Governance v1 exists to make engineering faster, safer and easier to manage. It is not a governance product.

1. **Reuse before building.** Extend GRS, existing manifests, contracts and workflows before adding machinery.
2. **Roadmap ≠ Issues ≠ PRs.** Roadmaps own milestones/priorities; Issues own independently actionable work, bugs and blockers; PRs provide implementation evidence. Tiny changes do not require Issues.
3. **One owner per status.** Do not copy mutable completion state into ROADMAP, TASKS, Issues and reports. Reference the canonical owner instead.
4. **Standardize discovery, not file locations.** Existing roadmap/tracker paths remain valid; discovery tells an agent where canonical local sources are.
5. **Preserve local authority.** Specialized product, execution, readiness and design trackers may coexist when their responsibilities differ; reconcile contradictions instead of flattening useful documents.
6. **AI BASE stays tiny.** Inventory existing AGENTS.md, Cursor rules, skills/hooks and CI before proposing shared agent guidance. Prefer a minimal shared contract plus tool-specific adapters only where needed.
7. **No new infrastructure by default.** No database, dashboard, service, scheduler or universal agent framework without demonstrated recurring need.
8. **No milestone inflation.** Governance v1 stays GOV-M01–M08 and overlays existing M0–M10.
9. **Prioritize execution.** Contract acceptance and practical pilot evidence come before broader rollout.
10. **Stop building when maintenance exceeds verified value.** Defer or reject proposals that add more governance cost than demonstrated benefit.

## C01 — Source of Truth

1. GitHub is authoritative for accepted engineering artifacts: code, merged pull requests, Issues, ADRs, repository governance and repository-local roadmaps.
2. The default branch is the accepted repository state unless an explicit repository policy defines another canonical branch.
3. An open PR or feature branch is proposed evidence, not accepted canonical state.
4. Career Intelligence retains semantic authority over career facts, evidence and provenance.
5. PostgreSQL remains the canonical runtime career store after import/canonicalization.
6. Engineering Handbook Git owns canonical theory.
7. Engineering Labs Git owns practice definitions and artifacts.
8. Product repositories own their implementations.
9. External schedulers/runtime platforms remain authoritative for live scheduler/runtime state.
10. Chat memory is context, never independent completion evidence.

Existing mechanisms:
- `grs/OPERATING-MODEL.md`;
- `reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md`;
- `autopilot-control-plane/CONTROL_PLANE.md`;
- repository-local roadmaps and policies.

## C02 — Roadmap Integrity

1. Existing repository roadmaps remain canonical in their own bounded contexts.
2. This initiative does not replace or renumber M0–M10.
3. Governance tasks use stable GOV identifiers.
4. Defects discovered during execution remain visible; do not hide them to protect percentages.
5. Historical decisions and superseded tasks remain traceable.
6. Status changes require repository evidence appropriate to the claimed stage.
7. A central registry, if approved, may point to roadmap locations but must not copy mutable task percentages.

Existing mechanisms:
- HQ `[NEW]` task rule;
- Control Plane fixed release baseline / no-moving-goal rule;
- Haversine human roadmap;
- repository-local task/readiness documents.

## C03 — Agent Execution

1. Every mutation begins with fresh default-branch, open-PR, target-head and CI inspection.
2. Work must remain inside the actor's explicit repository and domain scope.
3. Exact-head verification is required before bounded autonomous merge.
4. Changed heads, red required CI, ambiguous ownership or overlapping worker surfaces stop the merge path.
5. Scheduled workers must not change their own scheduler configuration.
6. Consequential owner gates remain owner-only.
7. Execution budgets favor bounded attempts and strategy changes over repeated equivalent retries.
8. A repository-local discovery entrypoint may tighten these rules but cannot weaken global safety boundaries.

Existing mechanisms:
- `governance/autopilot-merge-policy.json`;
- `governance/AUTOPILOT-MERGE-SAFETY.md`;
- Control Plane `AUTHORITY.md`;
- repository-local worker/agent policies.

## C04 — Evidence & Completion

Use these evidence stages as vocabulary, not as a new status database:

- **planned** — accepted task exists;
- **implemented** — change exists in a branch/working change;
- **tested** — relevant checks passed for an exact head;
- **merged** — accepted into the canonical branch;
- **deployed** — deployed to the intended runtime/environment;
- **released** — published/tagged/released to the intended consumer surface;
- **runtime-verified** — behavior verified from the target runtime or published artifact.

Rules:

1. Later stages imply evidence, not merely documentation text.
2. `implemented` is not `merged`.
3. `merged` is not automatically `deployed` or `released`.
4. `released` is not automatically `runtime-verified`.
5. Documentation saying DONE cannot overrule missing required evidence.
6. Repository-specific acceptance gates remain authoritative.

## C05 — Cross-Repository Authority

- `.github` owns GitHub-wide governance architecture and GRS.
- `autopilot-control-plane` owns fleet scheduling/telemetry/worker-health governance; external scheduler live state remains externally authoritative.
- `listing-kit` owns Ladvero implementation/product state.
- `career-intelligence` owns Career Intelligence product/platform state and semantic career-data boundaries.
- `engineering-handbook` owns theory.
- `engineering-labs` owns practice definitions/artifacts.
- `haversine-geolocation` owns Haversine OSS/API/release state.

Cross-repository governance may validate boundaries and evidence but must not silently become product management.

## C06 — Security, Reliability & Cost

1. Never weaken security, tests, evidence semantics or owner gates to obtain a green result.
2. Use least privilege and immutable/pinned workflow dependencies where supported.
3. Secret scanning remains a baseline, not a substitute for private-content/history review.
4. Retry/churn suppression is required for repeated equivalent external failures.
5. No new service, database, dashboard, GitHub App or recurring worker is added without repeated evidence that existing Git-native mechanisms are insufficient.
6. Stable releases, visibility changes, credential operations and destructive history changes remain consequential owner gates.
7. Prefer subtraction and reuse over governance infrastructure growth.

Existing mechanisms:
- GRS policy-as-code;
- secret scans;
- Control Plane stop-building contract;
- default-deny merge policy.

## C07 — Reconciliation & Reporting

1. Reports are reconstructed from current GitHub/runtime evidence, not chat memory.
2. The owner-facing HQ roadmap records cross-repository progress and newly discovered gaps.
3. Domain repositories retain their own local completion truth.
4. Control Plane reconciliation retains runtime/fleet health truth within its scope.
5. Drift checks must be read-only unless a separate bounded repair is explicitly authorized.
6. Conflicting records resolve by authority and freshness.
7. Reports must expose blockers and stale evidence rather than normalizing them away.
8. GOV adoption should add pointers and validation, not duplicate live status.

## Conflict order

When rules overlap:

1. safety / owner approval boundary;
2. explicit canonical domain authority;
3. central GitHub governance;
4. repository-local governance;
5. worker/runtime prompt;
6. chat context.

A lower layer may tighten safety but must not silently weaken a higher-level constraint.

## Draft acceptance state

C01–C07 are reconciled against current GRS, HQ and Control Plane rules.

This document remains a draft until the proposed cross-repository authority deltas are owner-approved. No repository is required to add or change a local entrypoint solely because this draft exists.
