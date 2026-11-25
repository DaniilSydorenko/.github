# AI Engineering Delivery Governance — v1 (2026-11-18)

## Delivery-first pilot override (2026-11-25)

For #164 only, this section supersedes older planning, cadence, delegation-discovery and reporting requirements, not security or domain authority. The current goal is one accepted #217 agent result, not a general orchestration platform.

- One existing implementation PR, one writer, one coherent fix per round. Direct connector edits are the default for bounded HQ fixes; no mandatory Cursor evaluation or paid delegation.
- Read the active PR and relevant code once; implement the complete known blocker in the same round. Do not repeat unchanged audits, status-only rounds, roadmap estimates or create new helpers unless necessary for a working path.
- Reuse the protected workflow, App writer, durable CAS/replay ledger, provider cap, scope validation and required exact-head CI. No new service, scheduler, credential, ruleset or abstraction. Never bypass protections or fabricate acceptance.
- Check only changed dependencies and required gates. Run focused regression tests and existing required CI once per final HEAD; poll only when a result can change the next action. Fresh live authorization and security evidence remain mandatory at execution.
- Recovery is an explicit terminal rejected-result path, not successful integration. Preserve history; prove terminal execution and rejected artifact, then admit at most one bounded correction for #217. No parallel writers or automatic merge.
- Finish #192, recover the lease, execute #217, review the actual snippet and exact-head CI. #226 and all platform expansion are deferred until owner acceptance. Escalate an actual owner-only action once, with exact instructions.
- Report only changed code/PR, test result, actual blocker and next action. If no mutation is possible, state the concrete tool or authority limitation; do not imply progress.


**Status:** proposed in AI-ENG Draft PR #166; not organization-wide enforcement until merged and adopted. **Owner:** Daniil. This contract governs the *way* engineering work is planned and reported; it never grants execution, merge, billing, security or cross-repository authority.

## Owner-time budget and operating mode

- Owner typically checks in briefly, a few times per day, **not an eight-hour shift**. Aim for **10–20 minutes of owner attention per day**, as a planning target, not an obligation.
- Work in bounded **AI sessions** with verifiable deliverables, not unqualified eight-hour “engineering days”. Separate elapsed calendar time, engineer-effort estimates and owner-attention estimates. Never imply a model works continuously between chat turns unless an authorized scheduler/worker actually runs.
- One owner decision per session at most when feasible; do independent safe technical research and implementation without asking for routine choices. Never trade safety for speed.
- A “continue” request means resume the canonical existing plan and current issue/PR; do not invent a new roadmap, duplicate task, branch or executor.
- At the start of a new chat, **recover current state from repository sources**: local AGENTS.md, canonical delivery plan, active issue/PR, exact HEAD and CI. Memory or a previous chat summary is a hint, not operational evidence.

## Mandatory delivery artifacts

Every nontrivial initiative must have **one canonical delivery plan** in the owning repository, linked from the initiative's existing tracking Issue and implementation PR. Minimum fields:

1. Objective and measurable Definition of Done, in/out of scope, safety and authority limits.
2. Task IDs with priority, dependency, owner, status, acceptance test, estimate **in bounded AI sessions** and conditional calendar checkpoint.
3. Evidence-backed blocker register with stable IDs, severity, impact, owner, resolution criteria and **UNKNOWN** inventory; never claim the register is exhaustive until a defined audit closes.
4. Status gates: G0 change sanity; G1 safety contracts; G2 integrated end-to-end chain; G3 real operational enforcement; G4 pre-execution admission. A green unit/CI check cannot imply live readiness.
5. Forecast confidence, assumptions, last verified SHA/CI, explicit changes to scope or target date.
6. Rollback/STOP criteria, budget/permissions/security/merge approval boundaries.

## Work-in-progress and change control

- Prefer **one active implementation PR per initiative**, small sequential changes, no competing writers; unrelated product work remains owned by its repository.
- Before implementation, run **inventory and dependency mapping** (actual launch paths, credential holders, permissions, schedulers, branches and failure modes). An unverified path is a blocker, not an implicit PASS.
- Before each commit: define its task ID and acceptance test. After each commit: fast zero-model tests and exact-head CI. On execution/lease changes add negative end-to-end failure drills; before live do authenticated configuration/budget checks.
- **No speculative helper modules** while an earlier critical integration dependency remains unverified, unless a bounded change is itself needed to establish that evidence.
- New P0/P1 blocker: record it, assign evidence/owner, update critical path and forecast, and stop unsafe dependent work. Do not silently expand the roadmap.
- No uncontrolled retry, duplicate agent, automatic merge, release, permission/secret/billing change or paid model invocation. Existing domain and owner gates remain authoritative.

## Status report contract (short)

Each active session ends with:

`HEAD / CI | completed task IDs | open blockers (known + unknown) | G0–G4 | next task | forecast delta | owner action (none / one precise decision)`.

Report **implemented in branch**, **CI verified**, **merged**, **deployed** and **operationally enforced** as different facts. Never say “done” based solely on code existing.

## Cross-repository adoption

This policy is a **shared reference**, not a magic GitHub inheritance mechanism. Repository-local AGENTS.md, protected CI and authorized workers are needed for enforceable behavior. GitHub's central `.github` repository may supply shared community files, but cannot be assumed to override local instructions or enforce agent execution in every existing or future repo.

- **Existing repositories:** inventory first; propose one small, repository-owned adoption PR per repo only with owner authorization and no conflict. Include local `AGENTS.md` pointer, a local delivery-plan location, appropriate CI contract and domain-specific restrictions. Do not mass-write or auto-merge.
- **Future repositories:** create from a controlled repository template/bootstrap checklist that includes `AGENTS.md`, delivery-plan skeleton and CI. Template use is an explicit repo-creation choice, not an automatic guarantee.
- **Runtime enforcement:** required checks/rulesets and credential-scoped execution are independently configured and verified per repository; documentation alone is advisory.
- Adoption states: `NOT_INVENTORIED`, `CANDIDATE`, `PR_OPEN`, `CI_PASS`, `MERGED`, `ENFORCED`. No false “all repos covered” assertion.

## New chat bootstrap

Suggested owner prompt (optional, not required for a connected agent that can discover the repo):

> Continue the AI Engineering initiative. Read the owning repo's AGENTS.md and canonical delivery plan, inspect the active Issue/PR and exact-head CI, then perform the next safe bounded task. Follow the delivery governance contract; report blockers and owner decisions. Do not start paid work, merge or change permissions without the required approval.

**Limit:** ordinary ChatGPT chats do not automatically execute repository files as system instructions. To reliably carry these rules into new chats, add them to persistent Project instructions (human action) and keep the repo plan as source of truth. The agent must actually retrieve the current plan. Connected autonomous workers need explicit instruction injection/bootstrap and independent enforcement.
