# AI Engineering Ecosystem — Nine-Phase Roadmap

**Status:** OWNER RESEARCH INITIATIVE / NON-ENFORCING / PILOT STAGE  
**As of:** 2026-10-22  
**Owner:** Daniil (personal engineering initiative; not GitHub HQ or a scheduled Autopilot worker)  
**Canonical strategy for this initiative only:** this file. Product, GitHub HQ, Control Plane, and worker roadmaps keep their own authorities.  
**Related:** [Operating Rules](OPERATING_RULES.md) · [Budget & Measurement](BUDGET_AND_MEASUREMENT.md)

## Mission and target experience

Eliminate human copy/paste as the transport between ChatGPT, GitHub and Cursor, then enable **bounded, evidence-driven agent execution** at an acceptable cost and with minimal owner attention.

Desired path: **owner describes an outcome in ChatGPT → ChatGPT creates bounded GitHub issue/PR task → Cursor Cloud executes → existing repository tests/CI provide proof → ChatGPT reviews GitHub evidence when invoked → owner explicitly approves consequential integration/release**.

This ChatGPT conversation is a *human decision interface*, **not** a continuously running background controller. An agent may continue within its supported Cursor session or automation only when a separate execution contract and platform mechanism explicitly authorize it. GitHub is the transport and source of engineering evidence; it does not transfer ChatGPT memory, connector access or execution authority to the agent.

**Optimization objective:** accepted useful results per unit of **money + owner attention + elapsed time**, with safety and regression constraints always binding. Do not optimize commits, PR count, token count or roadmap percentages as outputs.

## Progress vocabulary

- **VERIFIED:** a documented acceptance experiment exists, tied to live GitHub/CI/provider evidence, *for the specific capability claimed*.
- **PARTIAL:** some steps proven, essential exit checks pending.
- **NOT STARTED:** concept only; no tested implementation.
- **BLOCKED:** exact missing permission, environment or decision with evidence.
- **N/A:** capability not needed unless a verified gap emerges.

Statuses below describe the *AI Engineering initiative*, not Haversine's 88% or GitHub HQ's milestone score. **No synthetic phase percentage.** Each gate is independently accepted or open. Never copy mutable product roadmap data here.

## Current verified baseline (2026-10-22)

- **Pilot 01:** [Haversine issue #173](https://github.com/DaniilSydorenko/haversine-geolocation/issues/173). ChatGPT used GitHub to dispatch a strictly read-only task through `@cursor`. Cursor Cloud launched, read the scoped files, and its normal `cursor[bot]` comment carried the answer back to GitHub; ChatGPT re-read and checked the facts. A direct agent-side `addComment` call failed, so **agent-native write via that tool is NOT VERIFIED**. The standard Cursor completion update worked. Issue closed.
- **Pilot 02:** [task #174](https://github.com/DaniilSydorenko/haversine-geolocation/issues/174) → [Cursor-authored PR #175](https://github.com/DaniilSydorenko/haversine-geolocation/pull/175). A real V2 pole-distance regression was reproduced and fixed in two scoped files, with regression tests, owner-reviewed diff and **10/10 applicable exact-PR-head CI jobs** verified. Owner-authorized squash merge: [`029faec92c1821fca343595d1fefa423d21b9c62`](https://github.com/DaniilSydorenko/haversine-geolocation/commit/029faec92c1821fca343595d1fefa423d21b9c62). Roadmap sync [PR #176](https://github.com/DaniilSydorenko/haversine-geolocation/pull/176) merged at [`7ca9456b33761cda2b6e52aeef5df8ff157f6f5b`](https://github.com/DaniilSydorenko/haversine-geolocation/commit/7ca9456b33761cda2b6e52aeef5df8ff157f6f5b). **Push-triggered post-merge CI not independently retrieved with the connector and remains UNKNOWN**; PR CI must not be substituted.
- **Provider configuration observed from owner's screenshots:** GitHub App connected; Cursor Cloud available; outbound network reduced to provider defaults + user allowlist; model dropdown showed `composer-2.5-fast`. These are an observed snapshot, **not guarantees of current model, billing cap, future permissions or universal availability**.
- **Cost per pilot:** UNKNOWN. No actual per-run billing/charged usage was independently read. The displayed aggregate token count and included/on-demand usage are not an individual task cost.
- **Next:** Pilot 03 — prove continuation on the **same existing PR and branch** with one active writer, review response, updated exact-head checks, and measured incremental usage. Avoid repeating Pilot 01/02 to generate activity.

## Phase 1 — Foundation and spending safety — PARTIAL

1. **GitHub Audit** — identify the canonical repo authorities and only relevant current conflicts. **VERIFIED for Pilot 01/02; not a recurring fleet sweep.**
2. **Cursor Cloud** — confirm GitHub integration, account access, outbound restrictions and usable cloud environment. **VERIFIED for Haversine pilots.**
3. **Integrations** — prove ChatGPT ↔ GitHub ↔ Cursor via the actual comment and PR surfaces. **VERIFIED at pilot scope.**
4. **Pilot Selection** — choose bounded, independent reproducible experiments. **VERIFIED.**
5. **Billing Baseline** — inspect model actually billed, account spend ceiling/on-demand state and pilot usage. **OPEN.**

**Exit:** basic transport passes, sensitive network/secret boundaries preserved, provider-side spending controls reviewed, actual pilot usage captured or explicitly UNKNOWN.

## Phase 2 — No manual copy/paste — PARTIAL

1. **Task Creation** — ChatGPT records a short source-linked task in GitHub. **VERIFIED.**
2. **Agent Trigger** — GitHub `@cursor` starts authorized Cursor Cloud task. **VERIFIED.**
3. **Execution** — Cursor reads repo and executes one bounded task. **VERIFIED.**
4. **Result Handoff** — completion and PR evidence flow back to GitHub for ChatGPT to inspect. **VERIFIED.**
5. **Review Loop** — ChatGPT issues follow-up to existing PR; Cursor incorporates it and reports back, **without new competing work**. **OPEN.**
6. **Deduplication** — avoid double-dispatch/repeated bot mentions. **OPEN for automated triggers.**

**Exit:** two-way follow-up confirmed, at least one corrected task accepted with no manual prompt/result transport, explicit prevention of duplicate launches.

## Phase 3 — One PR, one active writer — PARTIAL

1. **PR Binding** — target a specific existing PR/head branch. **OPEN.**
2. **Branch Lease** — enforce at most one active writer; provider `agent_busy` does not protect desktop vs cloud alone. **OPEN.**
3. **Session Continuity** — continue an existing Cursor agent/run without accidentally starting a new one. **OPEN.**
4. **Device Switching** — safe handoff from MacBook to Cloud, with pushed state first and a fresh read on return. **OPEN.**
5. **Conflict Protection** — read relevant open PR changed paths before edit/merge. **VERIFIED manually for Pilot 02; enforcement OPEN.**

**Exit:** a real PR follow-up with unchanged branch ownership, serial execution, audited latest HEAD, and no competing writer.

## Phase 4 — Autonomous verified engineering loop — PARTIAL

1. **Discover & Plan** — live baseline, applicable repo policy, bounded acceptance contract. **VERIFIED once.**
2. **Implement** — isolated scoped code/test change. **VERIFIED once.**
3. **Verify** — focused checks, repository-required CI and exact-head evidence. **VERIFIED for Pilot 02.**
4. **Self-Correction** — react to a failed test/CI with diagnosis and limited retry. **NOT VERIFIED; no observed failure loop.**
5. **Stop Rules** — no release/merge without authority; stop on blocked scope or budget. **INSTRUCTIONS USED; technical enforcement OPEN.**
6. **Completion** — concise PR plus evidence or transparent BLOCKED/INCONCLUSIVE. **VERIFIED once.**

**Exit:** fail→diagnose→repair→recheck or safe stop in a single agent workflow; no unsafe scope expansion; measured attempt count.

## Phase 5 — Fresh context and outcome visibility — PARTIAL

1. **Context Package** — assemble relevant canonical sources at task start, not a copied second truth store. **MANUAL/OPEN automation.**
2. **Task Contracts** — goal, base SHA, allow/deny paths, risks, proof, attempt budget. **VERIFIED for pilots.**
3. **Evidence Reports** — exact HEAD, tests, merge/release separation, UNKNOWN states. **VERIFIED for pilots.**
4. **Progress Tracking** — accepted outputs and current blockers; no invented percentages. **PARTIAL; source reading is on-demand.**
5. **Cost Tracking** — per-run usage, charged cost, owner interventions and verified outcome. **OPEN.**

**Exit:** for three comparable real tasks, reproduce provenance and report cost/attention/outcome from provider/GitHub evidence without manual transcription or a new status DB.

## Phase 6 — Minimal dispatcher (optional) — NOT STARTED

1. **Gap Analysis** — determine what GitHub events, Cursor subscriptions and API cannot already do.
2. **Execution Bridge** — only if needed, bounded TypeScript interface to existing Cursor API.
3. **Task Queue** — owner-approved eligible work only; no domain roadmap takeover.
4. **Event Handling** — dedupe webhooks, handle timeouts, CI completion and cool-down.
5. **Optional GPT API Agent** — separate programmatic OpenAI client only if justified; **not** this ChatGPT thread or its memory.

**Exit:** documented repeated integration gap + measured benefit of the smallest bridge. **N/A** if native GitHub/Cursor solves the use case. No custom scheduler by default.

## Phase 7 — Harness² / reproducible agent experiments (optional) — NOT STARTED

1. **Harness Setup** — isolated laboratory; verify project license, provenance and executor capability first.
2. **Model Integration** — supported executors; Cursor integration requires a validated adapter, not an assumption.
3. **Agent Experiments** — compare prompt/rules/skills/tools on fixed test tasks.
4. **AutoResearch Loop** — bounded hypothesis→change→measurement→keep/revert.
5. **Benchmark Evaluation** — correctness, regressions, total cost, attention, safety and unseen tasks.
6. **Harness Promotion** — human-reviewed candidate config, never automatic policy weakening.

**Exit:** replicated improvement across an unseen test set without quality/safety regression and within a separate experiment budget; otherwise stop.

## Phase 8 — Cross-project validation — NOT STARTED

1. **Haversine** — baseline proof exists; use as narrow numeric/compatibility pilot, no Haversine Autopilot.
2. **Ladvero** — independently approved, low-risk Nuxt/UI/API test; no autonomous product redesign, billing or release.
3. **Career Intelligence** — synthetic or approved de-identified ingestion/provenance fixtures; no private-source leakage.
4. **Handbook & Labs** — executable learning/evaluation tasks without converting learning into VERIFIED work history.
5. **Shared Capabilities** — extract reusable mechanisms only after two distinct independent consumers.

**Exit:** repeated verified value in at least two distinct product types, respecting their owners and canonical source documents.

## Phase 9 — Engineering Control Plane product decision (optional) — NOT STARTED

1. **Unified Control** — only a proven missing owner interface, not another roadmap/dashboard.
2. **Agent Registry** — authorized executor/config discovery, not write authority.
3. **Model Routing** — quality/latency/charged cost decision grounded in measurements.
4. **Policy Engine** — enforce executable least privilege after demonstrating prompt-only limitations.
5. **Context Compiler** — source-backed, scoped, fresh reproducible package; not persistent duplicate state.
6. **Continuous Improvement** — deliberate evaluated promotions, no self-modifying authority.
7. **Product Evaluation** — user demand, competing tools, security and unit economics.

**Exit:** separate owner GO after benefits/risks/cost and demand are proven. Otherwise keep the lightweight GitHub/Cursor solution.

## Next ordered experiments (not standing automations)

1. **Pilot 03: PR follow-up continuity** — one existing scoped PR, one writer, one review comment, one evidence-backed correction, measured cost.
2. **Pilot 04: self-correction** — small deterministic failing test, at most two evidence-based corrections, exact-head CI or stop.
3. **Pilot 05: Ladvero limited use** — independently approved frontend task; no cross-domain authority transfer.
4. **Cross-task evaluation** — compare the first three outcomes by owner interventions, actual billed usage and accepted tests.

## Independent boundaries — no reorganization of existing systems

- [GitHub HQ roadmap](../../../reports/github-hq/ROADMAP-LIVE.md) owns GitHub **infrastructure only**; this initiative is **not** an HQ milestone and does not reopen frozen Governance v1 or issue #56 Option B.
- [HQ/autopilot boundary](../../../reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md) forbids HQ domain PR management. Initiative experiments require the **relevant domain owner's permission**; a ChatGPT-to-Cursor task is not universal write authority.
- [Autopilot Control Plane](https://github.com/DaniilSydorenko/autopilot-control-plane/blob/main/CONTROL_PLANE.md) owns scheduled fleet governance and telemetry; this initiative neither joins its fleet nor changes its scheduler, policy, reporting or approval.
- Domain roadmaps, AGENTS.md, CI, package/release state, publication and owner gates remain authoritative; this document never overwrites them.
- Public-safe descriptions only; no private customer/work data, credentials, billing exports or raw usage/account identifiers in this public repository.

**Change discipline:** Update this initiative file only on a meaningful acceptance/owner decision, in a small reviewed PR. No hourly polling, PR-count reports, percentage churn or self-generating governance tasks.
