# Engineering Governance v1 — GOV-M02 Authority & Conflict Matrix

Date: 2026-10-12
Status: COMPLETE for the observed checkpoint

## Authority matrix

| Concern | Canonical authority | GitHub HQ role | Autopilot role | Conflict rule |
|---|---|---|---|---|
| GitHub-wide governance / GRS | `.github` | architecture + acceptance owner | bounded implementation of approved governance work | central rule may be tightened locally, never silently weakened |
| Fleet scheduling / telemetry / runtime health | `autopilot-control-plane` + external scheduler live state | cross-repo acceptance only | Control Plane owns runtime model | external scheduler is live-state authority; no task-setting change without owner approval |
| ListingKit product roadmap | `listing-kit` | governance audit only | Ladvero worker owns approved bounded product work | HQ must not reinterpret product completion from governance artifacts |
| Career Intelligence product/data platform | `career-intelligence` plus CI semantic/runtime stores | governance/publication boundaries only | Career Ecosystem worker owns domain roadmap | career facts/provenance remain CI authority |
| Handbook theory | `engineering-handbook` | governance/publication boundaries only | Career Ecosystem worker owns domain work | Git owns theory; private personal overlay stays separate |
| Labs practice | `engineering-labs` | governance/publication boundaries only | Career Ecosystem worker owns domain work | Git owns practice definitions/artifacts; learning evidence is not automatically production evidence |
| Haversine OSS | `haversine-geolocation` | governance/release readiness within existing HQ scope | bounded maintenance where authorized | repository roadmap/release evidence wins over stale chat memory |
| Accepted implementation evidence | merged commit + repository CI/release evidence | reconcile/report | execute only within authority | docs saying DONE cannot override missing merge/test/release evidence |

## Conflicts / ambiguities found

### 1. Engineering discovery is not uniform

- Labs has a useful root `AGENTS.md`.
- Career Intelligence root `AGENTS.md` only protects Lovable history and is not a full engineering entrypoint.
- Handbook has no root `AGENTS.md` on the observed default branch.
- ListingKit has overlapping planning surfaces: `ROADMAP.md`, `TASKS.md`, and `docs/mvp/MVP_READINESS.md`.

Delta: define a minimal discovery contract without forcing a single roadmap format.

### 2. Roadmap semantics differ by repository

- HQ uses milestones and percentages.
- Control Plane uses fixed L0–L7 release checks and a no-moving-goal closeout.
- Haversine uses a human task roadmap.
- ListingKit splits strategic roadmap, execution tasks and readiness.
- Handbook uses stacked branch/PR progression.

Delta: C02 must preserve local models while requiring stable identifiers, explicit authority and truthful transitions.

### 3. Completion semantics are not globally standardized

Existing evidence distinguishes some of authored, implemented, tested, merged, published and runtime-verified. The distinction is strong in Haversine and Control Plane, but not uniform across all seven repositories.

Delta: C04 should define a shared vocabulary without introducing a duplicate status database.

### 4. Agent entrypoint discovery is uneven

GRS and Control Plane already provide strong global boundaries, but a newly authorized agent cannot discover the same minimum contract through one predictable local entrypoint in every repository.

Delta: C03/C05 should specify a minimal local entrypoint or manifest pointer. Do not copy full global policy into every repo.

### 5. Cross-repository authority rules exist but are distributed

The rules already exist across GRS, HQ/Autopilot boundaries, Control Plane and domain docs, but no single engineering-governance index maps all seven repositories.

Delta: C01/C05 need one central registry/index in `.github` that points to local canonical sources instead of copying their status.

### 6. Control Plane blocker must remain visible

Issue #139 is an unresolved scheduler-snapshot autonomy proof problem. Governance v1 must not claim runtime acceptance while the Control Plane fixed release baseline says otherwise.

Delta: C04/C07 must consume truthful blocker evidence and never normalize it away.

## Existing mechanisms already satisfying C01–C07

| Contract | Existing coverage | Remaining delta |
|---|---|---|
| C01 Source of Truth | GRS operating model; HQ/Autopilot boundaries; Control Plane authority hierarchy | seven-repo discovery index + local entrypoint gaps |
| C02 Roadmap Integrity | HQ `[NEW]` rule; Control Plane no-moving-goal rule; Haversine explicit task roadmap | common minimum identity/status/evidence semantics |
| C03 Agent Execution | Control Plane authority matrix; HQ live-state/exact-head rules; local agent policies where present | CI/Handbook entrypoints; reusable minimal execution contract |
| C04 Evidence & Completion | exact-head CI, release gates, post-publish verification, fail-closed GRS | shared evidence-stage vocabulary |
| C05 Cross-Repository Authority | HQ/Autopilot boundaries; Control Plane fleet scopes | central seven-repo authority registry |
| C06 Security, Reliability & Cost | GRS, secret scans, least privilege, stop-building rules, retry/churn suppression | minimal risk/budget declaration only where useful |
| C07 Reconciliation & Reporting | HQ live checks; Control Plane reconcile; worker telemetry | read-only registry/entrypoint drift validation |

## Proposed authority changes — NOT IMPLEMENTED

These are proposals for owner approval before rollout:

1. Designate a central seven-repository governance registry in `.github` as a discovery index only, never a second status database.
2. Require each governed repository to expose one predictable discovery entrypoint that points to its local roadmap, authority and evidence sources.
3. Allow GitHub Autopilot to consume only owner-approved GOV Issues / bounded governance tasks; no implicit product-roadmap authority is added.
4. Define a shared evidence-stage vocabulary: planned, implemented, tested, merged, deployed, released, runtime-verified.
5. Add read-only drift validation for registry pointers and entrypoint existence only after the pilot proves the model.

No scheduler, visibility, deployment, publication, evidence-promotion or product authority change is implemented by this document.
