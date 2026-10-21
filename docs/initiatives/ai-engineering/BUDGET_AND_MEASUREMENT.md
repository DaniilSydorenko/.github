# AI Engineering Ecosystem — Budget & Measurement

**Status:** initial **measurement protocol**, not account billing configuration or an executable spending limiter.  
**Scope:** owner-approved personal AI engineering pilots; public-safe only.  
**Related:** [Roadmap](ROADMAP.md) · [Operating Rules](OPERATING_RULES.md)

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
- **Outstanding UI check:** scroll further down in `Spending` to verify whether `on-demand` is enabled and the actual monthly overage cap (or documented account-level stop). **Never infer a cap from zero charges.** If desired, open the two cloud-icon rows or use provider-supported per-run usage details to measure each pilot's token breakdown; do not upload private invoices or billing CSVs to public GitHub.
- Sources: [Cursor usage and limits](https://prod.cursor.com/help/models-and-usage/usage-limits) · [Cursor legacy overages](https://prod.cursor.com/help/account-and-billing/overages) · [Cloud Agent Builds](https://cursor.com/docs/cloud-agent/builds).

## Mandatory budget modes

**Mode P0 — Controlled pilots (current default)**
- One explicit owner-approved agent invocation per bounded task. **No unattended automations or self-selected task queue.**
- One active writing agent per branch; no default subagents; at most **two distinct evidence-backed corrections** after initial attempt.
- Confirm selected model, context-window mode and Cursor **Spending** settings before starting a *larger* coding session.
- Keep **on-demand spending disabled or its limit at the minimum owner-accepted value, if supported**, until owner deliberately authorizes paid overages.
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
| Additional *on-demand* experimental reserve | **$10 per billing period maximum proposal**, **not set** | Owner to choose/confirm in account UI |

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

Minimum to examine: actual selected/billed model, per-run charged or included usage if available, whether on-demand is enabled, current spending cap, next reset date, subagent count and whether the cloud environment consumed unnecessary context. This does **not** block creating documentation; it blocks claiming measured budget performance and enabling automated queues.

## Evidence-based calibration gate

After ≥3 comparable completed tasks, compare:
1. Connector-only information retrieval versus launching a Cloud Agent for read-only tasks.
2. Short fresh context versus long continuing session **on the same branch**.
3. Non-Fast versus Fast (only when actual account can select both and task quality is comparable).
4. Additional retry cost versus first-fix quality.
5. Repeated CI/workflows versus required CI (never suppress security/exact-head requirements merely to save budget).

If no statistically or practically meaningful savings arise, keep the simpler workflow. **No token dashboard, pricing database or router service until a repeated genuine need is demonstrated.**
