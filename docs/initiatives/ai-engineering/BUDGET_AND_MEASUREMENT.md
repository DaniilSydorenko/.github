# AI Engineering Ecosystem — Budget & Measurement

## 2026-10-31 — GitHub Actions execution hold is NOT Cursor spend proof

The owner-triggered [AI Engineering Singleton Gate Tests #50](https://github.com/DaniilSydorenko/.github/actions/runs/41187585268) finished with all three jobs failed **before any runner steps**. GitHub's account-level Actions execution restriction is an **external availability gate**. Neither the credential probe nor offline Python tests ran; no code, credential, or provider-cost verdict can be inferred.

- GitHub Actions runner/CI proof is temporarily BLOCKED. Existing GitHub Connector read/write work and carefully scoped static analysis are independent of GitHub-hosted runner availability.
- Keep GitHub Actions account eligibility/budget distinct from Cursor Cloud model usage and [Low-Burn measurement #120](https://github.com/DaniilSydorenko/.github/issues/120). Never post payment details, account exports, private financial totals or keys publicly.
- Do not weaken required security checks, change billing, add a substitute privileged runner, launch extra Cursor tasks, or claim exact-head CI passed while Actions cannot execute.
- When owner restores Actions eligibility, manually re-run the existing read-scoped single-repo App probe from protected main, approve the environment and verify actual job steps and trusted probe output. A rerun with no steps is still BLOCKED, not PASS.
- Operational steps and stop conditions: [App owner setup handoff](APP_WRITER_OWNER_SETUP.md). Canonical [roadmap](ROADMAP.md) presently has an independent open editor [PR #144](https://github.com/DaniilSydorenko/.github/pull/144); do not create an overlapping writer.
**Status:** evidence protocol only — not verified live billing configuration or an executable spending limiter. Last owner account observation: 2026-10-22; recheck before any new provider launch.  
**Scope:** owner-approved personal AI engineering pilots; public-safe only.  
**Related:** [Roadmap](ROADMAP.md) · [Operating Rules](OPERATING_RULES.md)

## 2026-10-26 integration/billing evidence reconciliation

Merging HQ #133, #134 and #135 proves code integration and offline checks only. It is **not** a Cursor Cloud Agent pilot and proves neither paid/charged cost nor provider-wide singleton coverage.

Owner's most recent documented Cursor account setting was On-Demand Spending Disabled on 2026-10-22. No fresh account-level verification or per-run charged-cost attribution was obtained during this closeout. Provider usage/cost is `UNKNOWN`, never automatically `$0`.

Before any real managed Cursor launch, separately verify: account-scoped GET; all active runs; effective protected GitHub lease and exclusive writer; selected model/allowlist; current on-demand/BYOK boundaries; stable one-shot request identity; and owner acceptance for that precise task. Afterwards correlate provider run, tokens, actual charged/included usage and terminal proof. Do not enable recurring paid model runs or top-ups merely to obtain metrics.

[Provider and Low-Burn owner gate #120](https://github.com/DaniilSydorenko/.github/issues/120) remains OPEN until these runtime facts are demonstrated.


## What actually consumes what

| Activity | Cursor model usage | Other potential cost |
|---|---|---|
| ChatGPT conversation and GitHub Connector read/write | No **Cursor** model usage for this step | ChatGPT plan/tool limits; not universally free computation |
| GitHub issue/PR comment, webhook or `@cursor` trigger before execution | Trigger alone is not a Cursor inference run | GitHub platform limits |
| Cursor Cloud starts, reads code, calls model or subagents | **Yes**: model tokens billed under account terms | Depends on selected model, context and provider plan |
| Shell test/build itself | No model token charge **for running the command** | CI/runner resource or GitHub Actions minutes; interpreting logs costs agent tokens |
| GitHub required CI and merge | No Cursor tokens unless an agent consumes feedback/starts again | Actions minutes/storage and owner time |
| Harness/benchmark/model-comparison experiments | **Yes**, for every model-backed candidate run | Extra evaluation compute; keep separate budget |

Do not conflate raw tokens, cached tokens, included usage, charged dollars, API list price or GitHub Actions minutes. A personal screenshot showing `included` and `on-demand 0` for a period **does not** prove per-run zero cost or future free executions.

## October 2026 owner dashboard reconciliation (privacy-safe)

- Owner showed a **legacy Pro+** Spending view with **separate monthly Cursor Models and Other Models included pools** and a next usage reset date. Cursor Models includes first-party Composer and Grok; Other Models represents the third-party allowance. **Quota percentage is not USD charged**. Exact personal quotas and any billing exports remain private and should not be copied here.
- **October 21 UTC usage now observed:** owner screenshot shows two cloud-icon rows matching the pilot execution times: **22:30 UTC — `grok-4.7-high-fast` (Pilot 01 read-only)**; **22:49 UTC — `composer-2.5-fast` (Pilot 02 code fix)**. Both rows are classified `Included`. The selected-day aggregate shows **zero `On-demand` usage**. These are provider UI observations with high-confidence timestamp/agent correlation, **not per-run token or charged-cost breakdown**. Precise per-task input/output/cache usage, financial cap and enablement of future on-demand remain **UNKNOWN**. Earlier Oct 1 Included-only screenshots are historical background, not pilot billing evidence.
- Owner's Cloud Agent default `composer-2.5-fast` was observed, but the provider may use a different model when a run explicitly selects it. Do not infer per-run price from the default-model setting.
- The owner's Haversine **Recurring Environment Build** succeeded. Cursor documentation states these scheduled pre-builds refresh machine snapshots and **do not cost extra**; they are **not** autonomous coding-agent executions. Do not launch manual Builds or treat recurring Builds as token-consuming model loops. The environment may still start from a cached default-branch SHA, so each task must verify a fresh Git baseline and its feature branch.
- **Account-level safeguard VERIFIED (owner screenshot, 2026-10-22):** `On-Demand Spending: Disabled`; `Monthly Limit: Disabled`, with `Disabled` selected from `Fixed / Unlimited / Disabled`. **No active dollar-valued overage allowance exists in this setting.** Leave disabled for current P0 pilots. This controls additional on-demand charging but **does not reserve or preserve included model quota**, nor enforce a per-task token cap. Recheck only before future unattended runs or an owner-authorized settings change. For per-pilot cost calibration, inspect the two cloud-icon usage rows or provider-supported per-run details; never publish private invoices/CSV.
- Sources: [Cursor usage and limits](https://prod.cursor.com/help/models-and-usage/usage-limits) · [Cursor legacy overages](https://prod.cursor.com/help/account-and-billing/overages) · [Cloud Agent Builds](https://cursor.com/docs/cloud-agent/builds).

## Mandatory budget modes

**Mode P0 — Controlled pilots (current default)**
- One explicit owner-approved agent invocation per bounded task. **No unattended automations or self-selected task queue.**
- One active writing agent per branch; no default subagents; at most **two distinct evidence-backed corrections** after initial attempt.
- Confirm selected model, context-window mode and Cursor **Spending** settings before starting a *larger* coding session.
- Keep **on-demand spending Disabled (owner-confirmed 2026-10-22)**. If this changes, require explicit owner approval before additional agent runs or enabling unattended operation. Do not configure a nonzero or Unlimited overage allowance as a workaround for a stopped agent.
- Treat unknown cost as UNKNOWN and **do not launch another autonomous paid step** solely to complete an internal report.
- Owner must explicitly authorize changes to usage limits, account billing, secrets and recurring launches.

**Mode P1 — Limited automated follow-ups (future, separately approved)**
- Requires real measured pilot data, known provider-side spend ceiling, idempotent trigger, branch lease, fixed task scope, verified stop behavior and failure notification.
- No unconstrained auto-repeat or new-task chain. Trigger counts and usage reviewed after every limited experiment.

**Mode P2 — Cross-project/agent optimization (future)**
- Separate harness evaluation budget; compare to cheaper existing ChatGPT/GitHub workflow and account for all attempts/cached tokens, CI, review and regression impact.
- Promotion only after improvements reproducibly generalize.

## Initial soft envelopes — NOT technical account limits

| Task class | Planning envelope per run | Authority |
|---|---:|---|
| Narrow read-only code investigation (only when connector insufficient) | **up to $1** | Owner-authorized pilot |
| Focused fix + tests | **up to $3** | Owner-authorized, bounded code paths |
| Multi-file difficult diagnosis | **up to $5** | Separate owner approval; do not auto-upgrade |
| Additional *on-demand* experimental reserve | **$10 per billing period hypothetical future ceiling; NOT enabled** | Current owner setting: **Disabled**. Enabling a paid reserve would require a new explicit decision. |

These are *hypotheses* for learning, **not guarantees, historical spending or permission to incur charges**. Recalibrate after at least three comparable observed run costs. Never implement made-up dollar cutoffs inside a text prompt and call them enforced. Runtime dollar caps require tested provider support or a correctly designed API/SDK executor gate.

## Account controls and billing reality

- Cursor Cloud Agents use provider-documented model/API pricing; price and included pools depend on current account plan and selected model. Do **not** hardcode a `Composer`, `Fast`, `Grok` or `Claude` price in policy; check [Cursor Cloud docs](https://cursor.com/docs/cloud-agent) and [Usage & limits](https://prod.cursor.com/help/models-and-usage/usage-limits) at decision time.
- For legacy Pro/Pro+ accounts the **Spending** dashboard reports included pools and overages. Check **actual current account plan** rather than assume all plans share the same rules.
- Cursor notes spending-limit enforcement may not be instantaneous. Treat the account limit as a backstop, not proof of an exact per-task cutoff ([Cursor overage documentation](https://prod.cursor.com/help/account-and-billing/overages)).
- Cursor SDK docs describe per-agent `getUsage()` that can include raw and charged cents, with account feature availability differences. API/SDK **must be tested before depending on it for a per-task guard** ([TypeScript SDK](https://cursor.com/docs/sdk/typescript)). No SDK/API key or billing export is needed just to store this roadmap.
- Account's current **`composer-2.5-fast`** default was observed in a prior screenshot; **non-Fast availability and exact billable model in future runs are UNVERIFIED**. Before choosing a default for autonomous work, compare provider rates and real measured outcomes; avoid blanket claims about Fast being economical.

## Evidence schema (keep exact billing private; no new service)

```yaml
pilot_id: P02
task_ref: github-issue-or-pr-url
agent_ref: provider-agent-id-or-url
observed_at: iso-8601-timestamp
task_class: small-code
model_actual: known-value-or-UNKNOWN
agent_runs: integer-or-UNKNOWN
subagents: integer-or-UNKNOWN
input_tokens: integer-or-UNKNOWN
output_tokens: integer-or-UNKNOWN
cached_tokens: integer-or-UNKNOWN
raw_cost_usd: amount-or-UNKNOWN
charged_cost_usd: amount-or-UNKNOWN
included_vs_on_demand: known-value-or-UNKNOWN
elapsed_time: duration-or-UNKNOWN
owner_interventions: integer-or-UNKNOWN
result: SUCCESS | BLOCKED | INCONCLUSIVE | NO_IMPROVEMENT | REGRESSION | UNSAFE
pr_head_sha: sha-or-N/A
exact_head_ci: PASS | FAIL | UNKNOWN | N/A
post_merge_ci: PASS | FAIL | UNKNOWN | N/A
accepted_commit: sha-or-N/A
```

**Privacy boundary:** GitHub Issues/PRs in public repositories may show task identifiers, evidence, model category and cost status (`MEASURED_PRIVATE` / `UNKNOWN`), but **not** precise billed amounts, account identifiers, invoice exports or token logs that the owner considers private. Keep detailed charged cents and source data in the Cursor dashboard or a private owner-controlled location; no shared persistent cost database is required. The schema above is an internal analysis shape, **not** a requirement to publish these values.

**Primary metric:** `charged cost / verified accepted task`, always accompanied by **owner interventions**, **elapsed time**, **regressions** and **policy violations**. When `charged_cost_usd` is unavailable, report UNKNOWN; a `0` requires billing proof. Track total economic effort separately if desired, not falsely equate a usage pool debit to cash overage.

## First measurement action — no agent launch required

From **Cursor Dashboard → Spending / Usage**, manually review the billing-cycle status and model/runs associated with completed Haversine [Pilot 01 #173](https://github.com/DaniilSydorenko/haversine-geolocation/issues/173) and [Pilot 02 #174 / PR #175](https://github.com/DaniilSydorenko/haversine-geolocation/pull/175). Record only **non-sensitive aggregate measurements** in the matching existing GitHub task if owner chooses; keep raw invoices, account IDs, API keys, payment details and private CSV exports **outside the public .github repository**.

Minimum remaining measurement: actual selected/billed model (observed for pilots), per-run token split and equivalent/charged cost if available, agent/subagent count, and whether cloud execution consumed unnecessary context. The **on-demand enablement and current overage setting are already verified as Disabled**, not a pending UI task. This does **not** block creating documentation; it blocks claiming measured budget performance and enabling automated queues.

## Evidence-based calibration gate

After ≥3 comparable completed tasks, compare:
1. Connector-only information retrieval versus launching a Cloud Agent for read-only tasks.
2. Short fresh context versus long continuing session **on the same branch**.
3. Non-Fast versus Fast (only when actual account can select both and task quality is comparable).
4. Additional retry cost versus first-fix quality.
5. Repeated CI/workflows versus required CI (never suppress security/exact-head requirements merely to save budget).

If no statistically or practically meaningful savings arise, keep the simpler workflow. **No token dashboard, pricing database or router service until a repeated genuine need is demonstrated.**
