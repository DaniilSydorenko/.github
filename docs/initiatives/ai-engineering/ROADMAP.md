# AI Engineering Ecosystem — Nine-Phase Roadmap v2

**Status:** OWNER RESEARCH INITIATIVE / NON-ENFORCING / PILOTS 01–03 ACCEPTED / EXECUTION READINESS UNPROVEN  
**As of:** 2026-10-26 (live GitHub closeout; product readiness remains domain-owned)  
**Owner:** Daniil (personal engineering initiative; not GitHub HQ or a scheduled Autopilot worker)  
**Canonical strategy for this initiative only:** this file. Product, GitHub HQ, Control Plane, and worker roadmaps keep their own authorities.  
**Related:** [Operating Rules](OPERATING_RULES.md) · [Budget & Measurement](BUDGET_AND_MEASUREMENT.md)

## 2026-10-26 blocker correction: personal GitHub owner vs exclusive App writer

**New live fact:** `DaniilSydorenko/.github` is public but its GitHub owner
type is `User`, not `Organization`. The dedicated lease branch last reported
`protected:false`, and the protection GET was inaccessible to the current
connector (`403 Resource not accessible by integration`). No rulesets were
visible. Accepted PR #133 requires a protected ref with exactly one trusted
GitHub App writer and no human/team push rights. A regular personal-repo
branch protection rule is **not equivalent** to that exclusivity.

GitHub explicitly documents `Restrict who can push to matching branches` for
organization-owned repositories, not personal repositories:
https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule

**Therefore:** DO NOT instruct the owner merely to turn on a personal branch
protection rule and expect the current exact-app-writer gate to pass. GitHub HQ
owns an [explicit decision #108](https://github.com/DaniilSydorenko/.github/issues/108):
select a minimally invasive truly exclusive lease-writer authority, possibly
an organization-owned repository with app-only push restrictions, or another
equally enforceable CAS mechanism. Do not create/migrate any resource without
owner approval. Keep Cursor launch and unattended chaining disabled until
negative bypass and positive atomic-CAS tests prove real enforcement.

## 2026-10-26 accepted implementation and activation reality

The owner-requested closeout independently verified these squash merges on public HQ `main`:

- [#133](https://github.com/DaniilSydorenko/.github/pull/133), merge `1423ec59`: fail-closed live lease-ref protection audit before any managed Cursor POST. This does NOT configure effective GitHub protection.
- [#134](https://github.com/DaniilSydorenko/.github/pull/134), merge `7c2e3305`: bounded one-step next-Issue preview, stable request ID and existing-PR-first classification. This does NOT grant next-Issue launch.
- [#135](https://github.com/DaniilSydorenko/.github/pull/135), merge `435675d4`: pure terminal-run/PR verification, exact-head CI/Secret Scan checks, bounded correction proposals, owner/deploy/device gates. This does NOT make a model call or free the lease.

**Still blocked:** Last live GitHub read showed `ai-eng-cursor-lease-v1` `protected:false`. The accepted managed launch still contains `PILOT_ACTIVATION_ENABLED = False`. No authenticated continuous runtime, trusted private-domain event-to-execution adapter, effective exclusive writer, verified per-run billing or owner standing authorization exists. The public HQ repository must never store private domain Issue/PR/branch/SHA evidence.

**Next valid order:** protected lease + exclusive writer; account-scoped provider GET and billing safety; one separately approved bounded real Cursor pilot; independent terminal/exact-head checks and owner acceptance; durable release/recovery; only then a separately authorized one-at-a-time chain. [Owner gate #120](https://github.com/DaniilSydorenko/.github/issues/120) stays OPEN.


## Mission and target experience

Eliminate human copy/paste as the transport between ChatGPT, GitHub and Cursor, then enable **bounded, evidence-driven agent execution** at an acceptable cost and with minimal owner attention.

Desired path: **owner goal → domain-owned roadmap reconciled against accepted branch and existing PR/Issues → explicit eligible Issue/PR → one authorized Cursor writer → exact-head checks and bounded review/correction → owner/domain-controlled integration → evidence-backed roadmap acceptance**. A blocked PR in one domain must not stall independent eligible work in another.

This ChatGPT conversation is a *human decision interface*, **not** a continuously running background controller. An agent may continue within its supported Cursor session or automation only when a separate execution contract and platform mechanism explicitly authorize it. GitHub is the transport and source of engineering evidence; it does not transfer ChatGPT memory, connector access or execution authority to the agent.

**Optimization objective:** accepted useful results per unit of **money + owner attention + elapsed time**, with safety and regression constraints always binding. Do not optimize commits, PR count, token count or roadmap percentages as outputs.

## Progress vocabulary

- **VERIFIED:** a documented acceptance experiment exists, tied to live GitHub/CI/provider evidence, *for the specific capability claimed*.
- **PARTIAL:** some steps proven, essential exit checks pending.
- **NOT STARTED:** concept only; no tested implementation.
- **BLOCKED:** exact missing permission, environment or decision with evidence.
- **N/A:** capability not needed unless a verified gap emerges.

Statuses below describe the *AI Engineering initiative*, not any domain product's mutable task percentage or GitHub HQ's milestone score. **No synthetic phase percentage.** Each gate is independently accepted or open. Never copy mutable product roadmap data here.

## Current verified baseline (2026-10-22)

**2026-10-24 Low-Burn rollout accepted (documentation, not measured economy):** central [Issue template/rules #113](https://github.com/DaniilSydorenko/.github/pull/113), HQ [agent entry #114](https://github.com/DaniilSydorenko/.github/pull/114) and all six domain `AGENTS.md` PRs [Control Plane #179](https://github.com/DaniilSydorenko/autopilot-control-plane/pull/179), [LADVERO #245](https://github.com/DaniilSydorenko/listing-kit/pull/245), [Career #181](https://github.com/DaniilSydorenko/career-intelligence/pull/181), [Handbook #130](https://github.com/DaniilSydorenko/engineering-handbook/pull/130), [Labs #66](https://github.com/DaniilSydorenko/engineering-labs/pull/66), [Haversine #192](https://github.com/DaniilSydorenko/haversine-geolocation/pull/192) were confirmed merged and their entrypoints read from default branches. **This is 7/7 instruction availability, NOT automated consumption, token limits or verified savings.** [Provider-usage acceptance #120](https://github.com/DaniilSydorenko/.github/issues/120) is OWNER-GATED; no new Cursor executions just to collect metrics. Offline [Decision Gate #112](https://github.com/DaniilSydorenko/.github/pull/112) is accepted `main` research, not live provenance, an automatic agent router or permission to merge.

- **Pilot 01:** [Haversine issue #173](https://github.com/DaniilSydorenko/haversine-geolocation/issues/173). ChatGPT used GitHub to dispatch a strictly read-only task through `@cursor`. Cursor Cloud launched, read the scoped files, and its normal `cursor[bot]` comment carried the answer back to GitHub; ChatGPT re-read and checked the facts. A direct agent-side `addComment` call failed, so **agent-native write via that tool is NOT VERIFIED**. The standard Cursor completion update worked. Issue closed.
- **Pilot 02:** [task #174](https://github.com/DaniilSydorenko/haversine-geolocation/issues/174) → [Cursor-authored PR #175](https://github.com/DaniilSydorenko/haversine-geolocation/pull/175). A real V2 pole-distance regression was reproduced and fixed in two scoped files, with regression tests, owner-reviewed diff and **10/10 applicable exact-PR-head CI jobs** verified. Owner-authorized squash merge: [`029faec92c1821fca343595d1fefa423d21b9c62`](https://github.com/DaniilSydorenko/haversine-geolocation/commit/029faec92c1821fca343595d1fefa423d21b9c62). Roadmap sync [PR #176](https://github.com/DaniilSydorenko/haversine-geolocation/pull/176) merged at [`7ca9456b33761cda2b6e52aeef5df8ff157f6f5b`](https://github.com/DaniilSydorenko/haversine-geolocation/commit/7ca9456b33761cda2b6e52aeef5df8ff157f6f5b). **Push-triggered post-merge CI not independently retrieved with the connector and remains UNKNOWN**; PR CI must not be substituted.
- **Provider configuration observed from owner's screenshots:** GitHub App connected; Cursor Cloud available; outbound network reduced to provider defaults + user allowlist; model dropdown showed `composer-2.5-fast`. **Owner verified `On-Demand Spending: Disabled` and `Monthly Limit: Disabled` on 2026-10-22**; this means the extra on-demand charging path is currently off, not that the included subscription pool is unlimited or that individual tasks have dollar caps. Account settings may change; verify before unattended work.
- **Usage attribution:** owner Cursor Usage screenshot for Oct 21 UTC shows cloud-marked `grok-4.7-high-fast` at 22:30 (Pilot 01) and `composer-2.5-fast` at 22:49 (Pilot 02), both classified `Included`, and no `On-demand` for the selected day. This does **not** establish exact per-pilot tokens or charged USD; future on-demand behavior depends on the account setting remaining disabled. **Per-pilot cost: UNKNOWN.**
- **Pilot 03 ACCEPTED (2026-10-22):** [Issue #177](https://github.com/DaniilSydorenko/haversine-geolocation/issues/177) → [PR #178](https://github.com/DaniilSydorenko/haversine-geolocation/pull/178). Stage A produced North Pole `nearest()` test at `76ccbeaade69bce6960d1ddb8e9198708c6fac82`; ChatGPT issued exactly one owner-authorized review comment **on existing PR #178** for South Pole coverage. Cursor updated the **same PR and branch** `cursor/nearest-north-pole-regression-0b6f` and linked the **same provider Cloud session ID** `bc-e11ca7b4-d48d-4d8d-9f13-3a0f85df0b6f`, reaching exact head `45fbf48a119d1a09b6ed5a5183b95851cafd61ff`. Local focused tests (12), quality and typecheck reported PASS; independent [CI](https://github.com/DaniilSydorenko/haversine-geolocation/actions/runs/39754263327) and [Secret Scan](https://github.com/DaniilSydorenko/haversine-geolocation/actions/runs/39754263245) confirmed PASS on the exact PR HEAD. Owner-authorized squash merge [`9330b4585cc3d4ec9289c52f90730cf751a1fedc`](https://github.com/DaniilSydorenko/haversine-geolocation/commit/9330b4585cc3d4ec9289c52f90730cf751a1fedc); accepted `master` and issue closure verified. **No second PR/writer observed; this does not prove a technical branch lock. Post-merge push CI: UNKNOWN via connector. Per-run cost: UNKNOWN.** Haversine release/RC decisions are independent.
- **Next experimental gap:** Pilot 04 — **real failure → diagnosis → bounded correction → exact-head PASS or explicit STOP**. A fresh eligibility/collision preflight is mandatory before any task launch. Test branch handoff and per-run cost separately; no mass agent queue or repeated passed pilots.


## Seven-repository reassessment — what changed (2026-10-23)

Owner-directed, read-only discovery across exactly the seven repositories in [HQ registry](../../../governance/repository-registry.json) showed that **roadmap-to-Issue conversion is broadly achieved, but dispatch readiness is not**. This initiative does NOT take over domain PR triage, priorities or releases. The examples below are point-in-time **case studies and pointers**, not a shared mutable status database or a fleet dashboard. Re-read source at execution time.

| Repository | Learned constraint and current action authority |
| --- | --- |
| [GitHub HQ](https://github.com/DaniilSydorenko/.github) | HQ-specific closeout Issues [#107–109](https://github.com/DaniilSydorenko/.github/issues) exist. Owner-controlled publication [PR #82](https://github.com/DaniilSydorenko/.github/pull/82) remains separate. The initiative is **not** the HQ roadmap or fleet manager. |
| [Autopilot Control Plane](https://github.com/DaniilSydorenko/autopilot-control-plane) | Lean v3 L0–L7 is an accepted architecture. [Reported health](https://github.com/DaniilSydorenko/autopilot-control-plane/blob/main/state/latest.json) and [worker telemetry](https://github.com/DaniilSydorenko/autopilot-control-plane/tree/main/telemetry) demonstrate observation, **not accepted PR throughput**. Some historical incident references can outlive closed Issues. Never add another scheduler as a cosmetic cure. |
| [Ladvero](https://github.com/DaniilSydorenko/listing-kit) | **Fresh 2026-10-23 reconciliation:** [AI #212](https://github.com/DaniilSydorenko/listing-kit/pull/212) **MERGED** as `b514ef92`, [VI #215](https://github.com/DaniilSydorenko/listing-kit/pull/215) **MERGED** as `822e24b2`; [AI #216](https://github.com/DaniilSydorenko/listing-kit/pull/216) remains **OPEN** and overlaps six source/test/shared paths with already-merged #212, so its former independent green CI cannot prove integration on new `main`. Roadmap [draft #214](https://github.com/DaniilSydorenko/listing-kit/pull/214) and owning reconciliation [#235](https://github.com/DaniilSydorenko/listing-kit/issues/235) are still separate. Native iPhone, Gemini and full-history secret acceptance are independent owner gates. This is a time-bound example; **refresh again before a write**. |
| [Career Intelligence](https://github.com/DaniilSydorenko/career-intelligence) | PLATFORM, PUBLIC, DATA and ECOSYSTEM have distinct sources. Live production source [#131](https://github.com/DaniilSydorenko/career-intelligence/issues/131), DATA authorization [#166](https://github.com/DaniilSydorenko/career-intelligence/issues/166), website/API [#125](https://github.com/DaniilSydorenko/career-intelligence/issues/125) and hosting implementation [#174](https://github.com/DaniilSydorenko/career-intelligence/issues/174) are **not one Cursor job**. [R0–R23 index PR #173](https://github.com/DaniilSydorenko/career-intelligence/pull/173) is proposed only until owner acceptance. Never expose private source or silently promote career claims. |
| [Engineering Handbook](https://github.com/DaniilSydorenko/engineering-handbook) | Accepted [manifest](https://github.com/DaniilSydorenko/engineering-handbook/blob/main/automation/ecosystem-handbook-manifest.json) marks 30/188 topics authored, while a 188-topic draft is in a **stacked PR chain** rooted at [#64](https://github.com/DaniilSydorenko/engineering-handbook/pull/64); owner-gated [#91](https://github.com/DaniilSydorenko/engineering-handbook/pull/91) reconciles integration, [draft #84](https://github.com/DaniilSydorenko/engineering-handbook/pull/84) contains the detailed issue-linked roadmap. Do not regenerate chapters already drafted or equate a draft score with accepted main. |
| [Engineering Labs](https://github.com/DaniilSydorenko/engineering-labs) | [Master tracker #19](https://github.com/DaniilSydorenko/engineering-labs/issues/19) covers 14 milestones and 12 bounded agent contracts; [AG-01 #34](https://github.com/DaniilSydorenko/engineering-labs/issues/34) is a small read-only first exercise **if separately dispatched**. Scenario IDs remain unfrozen. Platform scaffolding may be agent-built; learner-owned BUILD/HARDEN/EVOLVE solutions must **never** be generated or marked complete by Cursor. |
| [Haversine](https://github.com/DaniilSydorenko/haversine-geolocation) | Stable **candidate 2.0.1** and exact-version manual staging capability were merged in [#190](https://github.com/DaniilSydorenko/haversine-geolocation/pull/190)/[#191](https://github.com/DaniilSydorenko/haversine-geolocation/pull/191), but canonical roadmap and [#187](https://github.com/DaniilSydorenko/haversine-geolocation/issues/187)/[#188](https://github.com/DaniilSydorenko/haversine-geolocation/issues/188) still reference 2.0.0 or pre-implementation states. **Reconcile/supersede before dispatch**; no public stable npm release proof here. |

**Accepted advisory offline research (2026-10-24):** [Decision Gate PR #112](https://github.com/DaniilSydorenko/.github/pull/112) implements offline fail-closed classification with 22 synthetic test cases and three manually sourced read-only dry-runs. Its input attestation is **not** automated GitHub evidence collection; live semantic matching, owner validation, writer leases, dispatch and issue synchronization remain unproven. The prototype is a separately reviewed experiment, not a new mandatory GRS/fleet control.

**Conclusion:** the highest-value missing capability is **delta-first eligibility and integration reasoning** over existing work, not backlog generation or more long-running workers. A domain blocked on acceptance, private data or a stacked PR does **not** globally block other eligible domains.

## Mandatory task routing contract — evaluated per authorized attempt

The following is a **decision procedure**, not a new fleet service, central queue, label mandate or GitHub HQ monitoring job. Prefer reading the owning repo's existing files and GitHub Issues/PRs instead of duplicating mutable status.

1. **Resolve authority:** identify the exact owning repository/lane and current `AGENTS.md`, domain roadmap, owner/worker permissions, security/QA/release gates. Cross-repository scope or unknown authorization means STOP / owner handoff.
2. **Refresh evidence:** read accepted default-branch SHA and target task, related Issues/PRs (including relevant changed paths, bases and proposed stacks), checks and deployed/provider evidence **only when relevant**. A task title, issue checkmark, roadmap %, mergeability and green PR CI are not sufficient alone.
3. **Classify the next action:** `ALREADY_ACCEPTED` (same accepted outcome), `SUPERSEDED` (owner-changed target with accepted replacement), `EXISTING_PR` (review/reconcile **that** PR), `READY` (independent bounded leaf with owner permission), `WAITING_DEPENDENCY`, `OWNER_GATE`, `EXTERNAL_BLOCKED`, `DEFERRED`, `UNSAFE`, or `NO_READY_WORK`. These are **ephemeral decisions**, not a second authoritative state store.
4. **Apply dependency and collision rule:** if same-file/semantic overlap, stacked base or another writer exists, choose an **integration/review action first** or stop. Do not infer lack of conflict from independent CI green, or rewrite/rebase another owner's branch. Never treat all old PRs as global cleanup prerequisites.
5. **Choose minimum-cost executor:** GitHub Connector for read-only inspection/document/issue preparation when sufficient; Cursor for a permitted implementation/verification leaf. **Issue creation alone is never a trigger.** No implicit auto-merge, owner approval, paid model upgrade, hosted data mutation or cross-domain worker activation.
6. **Close the loop:** require exact PR HEAD test/security evidence, accepted default-branch readback **after any authorized merge**, and separate deployed/registry/device/data proof wherever needed. Write the smallest useful outcome/blocked explanation into the **existing owning Issue/PR** and reconcile only its own roadmap.

**Hard stop:** unexpected HEAD, unapproved data/secret/billing exposure, failing required checks, two identical uninformative retries, unknown or changed owner scope, no remaining READY unit, or explicit human decision. Protected branch rule availability is provider/plan-dependent; prompt instructions and a same-session identifier do **not** constitute an atomic branch lease.


## Phase 1 — Foundation, permissions and spending safety — PARTIAL

1. **Transport/baseline:** GitHub App and Cursor Cloud verified for Haversine Pilots 01–03; owner/account/network constraints inspected. No permanent seven-repo write delegation.
2. **Secret and boundary safety:** least privilege, read-before-write, prompt-injection isolation and domain rules come before any pilot. Default model/quotas from current provider settings, not old screenshots.
3. **Billing guard:** last owner observation showed Cursor On-Demand Spending **Disabled** (2026-10-22); this is neither an unlimited included quota nor a per-task cost cap. Exact per-run token/charged usage remains UNKNOWN.
4. **Budget/abort evidence:** use [Budget & Measurement](BUDGET_AND_MEASUREMENT.md), keep invoices and private account identifiers out of public GitHub; stop if controls cannot be verified for unattended execution.

**Exit:** account/authority verified for the specific run, safe task contract and honest cost status. Do not re-audit the fleet for each agent.

## Phase 2 — GitHub as transport, no copy/paste — VERIFIED FOR MANUAL PILOTS

1. **Pilot 01:** read-only Issue #173 → @cursor → completion via cursor[bot] → ChatGPT verification. Agent-native GitHub comment mutation remains unverified.
2. **Pilot 02:** Issue #174 → PR #175 → tested scoped fix → explicit owner merge.
3. **Pilot 03:** Issue #177 → PR #178 → one authorized review comment → same PR/branch/session ID, exact-head green, owner merge.
4. **Non-goal:** successful synchronous transport does not mean that ChatGPT is a resident event processor or has delegated Autopilot permissions.
5. **Pending for unattended use:** duplicate-trigger/idempotency prevention under real notifications, retries and event delivery.

**Exit:** **met for owner-mediated task/review transport**; always-on automatic triggers remain OPEN. Do not repeat pilots to generate activity.

## Phase 3 — Delta-first work selection and integration preflight — PARTIAL / HIGHEST PRIORITY

1. **Roadmap coverage:** seven domain owners decomposed remaining work into local GitHub Issues/trackers; *coverage ≠ accepted implementation or READY-to-dispatch*. Read source per domain; no central copies.
2. **Accepted-vs-proposed discrimination:** distinguish accepted default branch, unmerged draft/stack, real deployed artifact and human-owner proof. Verified manually across seven repos; automation not proved.
3. **Dependency and ownership graph:** issue ↔ roadmap item ↔ existing PR/stack ↔ changed paths ↔ owner/data/release gate. Apply the mandatory classification above before running any new agent.
4. **Reconciliation-first:** already-implemented stale issues become evidence/supersession, overlapping PRs become one domain-owned integration order; do NOT launch a duplicate fix. Haversine #187/#188 and Ladvero #212/#216 are regression case studies.
5. **Independent progress:** if one domain says OWNER_GATE or WAITING, find an independently authorized READY task elsewhere, or honestly return NO_READY_WORK. Do not bypass a blocker.
6. **Observation consistency prototype — RESEARCH ONLY (PR #112, 2026-10-23):** offline `evidence_reconcile.py` and 15 additional synthetic checks confirm stale Issue/default-SHA/PR-head and unproven-acceptance cases fail to `NEEDS_EVIDENCE`. A one-time Ladvero #217/#216 stale-vs-fresh metadata exercise returned `NEEDS_EVIDENCE` / `launched:false`. This is **not** trusted automated live evidence capture, semantic matching, owner authorization, technical locking or accepted PR integration; milestone remains PARTIAL.

**Exit:** replay a **bounded set of real repo cases** including stale Issue, same-file overlap, stacked PR, production permission gate, learner-only work and genuinely READY task; each selects the safe action with no duplicate Cursor launch. Record actual outcomes, not guessed scheduling capability.

## Phase 4 — One writer, PR integration and safe device handoff — PARTIAL

1. **PR/session binding:** Pilot 03 verified a same-PR/same-branch/same-provider-session follow-up; identity alone does not prove mutual exclusion.
2. **Integration plan:** for overlapping AI code or Handbook stacks, review base and actual changed paths, determine authorized merge order, recompute exact-head checks after prior integration and perform fresh main readback. Green independent CI ≠ integrated result.
3. **One active writer:** human procedure verified in pilots; **technical branch/PR lease NOT VERIFIED**. Explore minimal GitHub/Cursor-native ownership signaling or tested conditional SHA gate before considering external locks; fail closed on ambiguous ownership.
4. **MacBook ↔ phone/cloud:** push state, release writer role, re-read branch/HEAD on destination and resume the same PR only if safe. Never run desktop and Cloud writers simultaneously.
5. **Authority:** domain owner decides reviews/merges and release; the initiative cannot merge arbitrary app stacks on HQ authority.

**Exit:** two nontrivial sequential integration/handoff cases with no duplicate writer, exact heads and bounded owner decisions; technical anti-race enforcement must be tested or explicitly recorded as unsupported/manual-only.

## Phase 5 — Bounded engineering loop and self-correction — PARTIAL

1. **Already shown:** plan → scoped fix/tests → PR → exact-head CI → owner review and revision (Pilots 02/03).
2. **Pilot 04 — NEXT engineering test:** one legitimate deterministic failing test/CI or a controlled failure **on an isolated task branch**, diagnose from actual evidence, apply up to two distinct bounded corrections, rerun checks and stop at reviewed PR; never intentionally break main or weaken required checks.
3. **No endless recovery:** repeat equivalent failure twice without new evidence → BLOCKED with fingerprint; unknown environment or external permission → STOP, not speculative workaround.
4. **Precise done:** code merge, deployed acceptance, npm distribution, real iPhone Safari, private Wave 2 and learner practice are **separate** facts. No pass-by-documentation.
5. **Policies:** no agent-generated learner solutions, private import or publication, auto-releases, unrestricted subagents, source mutation across owners or self-approval.

**Exit:** an observed FAIL → diagnosis → safe correction → exact-head PASS, or evidence-based BLOCKED, including attempt count and no authority expansion.

## Phase 6 — Fresh context, evidence and unit economics — PARTIAL

1. **Context preflight:** reconstruct only the task-relevant canonical docs, accepted SHA, live related PRs and owner constraints. Do not carry old chat assumptions or rescan all seven for every action.
2. **Evidence trace:** Issue → provider session → PR base/head → checks/review → accepted merge SHA → optional deployed/corpus/device/registry proof. Missing proof = UNKNOWN, not PASS.
3. **Cost measurement:** attribute model, tokens and actual charged vs included usage per run (if provider exposes it), owner interventions, elapsed time, accepted results and failed/repeated attempts. Pilot 01–03 dollar attribution remains UNKNOWN.
4. **Comparison:** compare equivalent small task types with/without agent, fresh vs continued session and correction effort. Do not confuse a GREEN scheduler or 100 generated Issues with productive accepted delivery.
5. **Data minimization:** no new cost/status database; private usage data remains in owner-controlled provider/account location, with safe summaries in existing Issues.

**Exit:** ≥3 comparable tasks with reproducible outcome + effort/cost evidence; if billing unavailable, honestly label UNKNOWN and do not claim cost savings or autonomous spending safety.

## Phase 7 — Cross-project execution proof, not mass dispatch — PARTIAL DISCOVERY

1. **Read-only foundation:** the seven-repo roadmap-to-Issue reconnaissance is done, but this **does not** count as proven independent Cursor execution in seven domains.
2. **Labs** is a clean bounded candidate: [AG-01 #34](https://github.com/DaniilSydorenko/engineering-labs/issues/34) read-only first, only after explicit owner launch; no learner-task solution or premature Scenario IDs.
3. **Ladvero** is an integration candidate **after** its active AI/VI/roadmap PR owners reconcile and authorize a nonoverlapping leaf. Do not send #217–219 into active same-file writers.
4. **Career Intelligence** can test synthetic-only, provenance-safe or docs-only leaves; no private workbook, production DB write, real employer claims, host publication or cross-owner approval.
5. **Handbook** demonstrates safe stack/integration routing; do not regenerate drafted chapters or count a draft as 188 accepted chapters. Haversine remains the numeric/compatibility control.
6. **External evaluator:** keep repository-specific CI, public-safe synthetic fixtures and owner human checks. Prefer one small pilot per distinct project type, not concurrent agent swarms.

**Exit:** at least two independent project types yield accepted useful results and correct WAITING/OWNER_GATE/NO_READY_WORK behavior, with zero duplicated work or security scope crossings. No fleet-autonomy claim from planning coverage alone.

## Phase 8 — Minimal orchestration and Harness² experiments (both OPTIONAL) — NOT STARTED

**Orchestration path — CONDITIONAL:** only after repeated evidence that GitHub/Cursor-native Issue/PR events and provider session continuation cannot safely implement the necessary READY-task transitions. Try native subscriptions/manual owner triggers first. A smallest adapter/dispatcher may be proposed **only** with: owner approval, actual event dedupe, target/branch lease, per-task opt-in, spend guard, retry/stop state, audit/rollback and explicit non-interference with the existing Autopilot scheduler. Do not assume this ChatGPT thread is an always-on worker.

**Harness² path — INDEPENDENT OPTIONAL RESEARCH:** isolated benchmark of prompts, skills, hooks, executors, context selection and model routing on safe synthetic/unseen tasks. Promote only replicated improvements in correctness, cost and owner attention; no automatic policy, security or billing modification. No new repositories or services until an independent, measured use case justifies them.

**Exit:** **N/A** is an acceptable result if native tools are sufficient. Otherwise a separate owner-approved smallest demonstrably necessary component, not a new default architecture.

## Phase 9 — Engineering Control Plane product hypothesis (OPTIONAL) — NOT STARTED

1. **Decision, not precondition:** consider a distinct ECP product only after repeated cross-project integration/permission/visibility friction cannot be solved within current provider/GitHub/domain ownership.
2. **Possible capabilities:** an owner-facing view of eligible vs blocked work, explicit executor/branch leases, reproducible context provenance, cost-aware routing, and permission decisions **only where actually supported**.
3. **Do not duplicate:** no competing Control Plane, domain roadmap database, worker telemetry store, fleet scheduler, governance engine or status dashboard solely for a nicer interface.
4. **Product gate:** assess alternatives, portability, access control, prompt-injection and private-data risk, reliability, demand and unit economics. Require owner GO and a narrow demonstrable MVP if ever warranted.
5. **Stopping criterion:** if original GitHub/Cursor workflow meets the goal safely and economically, do not build ECP.

**Exit:** independently justified owner product decision, not an automatic Phase 8 deliverable.

## Next ordered experiments and decision gates (not standing automations)

1. **First: task-readiness pilot** — classify existing same-file, stacked, stale-version and owner-gated cases from the above seven-repo examples; publish only links to owning issues/PRs, no new tracking database. Validate that selection rejects duplicate work.
2. **Pilot 04 self-correction** — once an owner authorizes a bounded relevant failure task, prove finite repair/STOP with exact-head checks and no unsafe retries.
3. **Pilot 05 independent second domain** — consider Labs #34 for read-only baseline and later a bounded implementation leaf; or a non-overlapping Ladvero fix only after its integration gate. **No mass Cursor launches.**
4. **Single-writer / device handoff** — verify desktop↔cloud transition; do not call GitHub PR binding an atomic lease.
5. **Per-task usage evaluation** — actual provider attribution if possible; only then evaluate an optional dispatcher or Harness experiment.

**All are conditional on owning-domain permission and a fresh per-task preflight; none authorizes a release, merge, deployed service, scheduler, billing change or new worker.**

## Original nine-phase approach — changes in v2

- **Retain:** nine phases, direct ChatGPT ↔ GitHub ↔ Cursor flow, owner approval gates, exact-head CI, Low-Burn and minimal infra.
- **Promote:** roadmap-to-Issue reconciliation, **delta-first eligibility**, PR integration/stack sequencing and dependency ownership to mandatory early gates (Phases 3–4).
- **Separate:** green telemetry, green individual PR CI, accepted default-branch integration and actual deployed/public/learning acceptance.
- **Reorder:** cross-project proof **before** optional orchestration/Harness work; build no dispatcher merely because Issues now exist.
- **Defer/remove from required path:** always-on scheduler, custom queue/DB, universal GitHub policy, automatic merge fleet, model router, full ECP product, repeated audits of all seven repos.
- **Record as unverified:** Pilot 04 self-correction, technical branch lease, Mac↔cloud handoff, per-run cost, unattended dedupe and safe automatic next-Issue selection.

## Independent boundaries — no reorganization of existing systems

- [GitHub HQ roadmap](../../../reports/github-hq/ROADMAP-LIVE.md) owns GitHub **infrastructure only**; this initiative is **not** an HQ milestone and does not reopen frozen Governance v1 or issue #56 Option B.
- [HQ/autopilot boundary](../../../reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md) forbids HQ domain PR management. Initiative experiments require the **relevant domain owner's permission**; a ChatGPT-to-Cursor task is not universal write authority.
- [Autopilot Control Plane](https://github.com/DaniilSydorenko/autopilot-control-plane/blob/main/CONTROL_PLANE.md) owns scheduled fleet governance and telemetry; this initiative neither joins its fleet nor changes its scheduler, policy, reporting or approval.
- Domain roadmaps, AGENTS.md, CI, package/release state, publication and owner gates remain authoritative; this document never overwrites them.
- Public-safe descriptions only; no private customer/work data, credentials, billing exports or raw usage/account identifiers in this public repository.

**Change discipline:** Update this initiative file only on a meaningful acceptance or owner decision, in a small reviewed PR. This v2 revision is a strategy proposal until accepted on HQ main; it cannot update any domain roadmap. No hourly polling, PR-count reports, percentage churn or self-generating governance tasks.
