# GitHub HQ — agent entry point

## Current operating mode: Maximum Safe Throughput (2026-11-28)

The #164 pilot is **complete** (#206 and #207 accepted). Current work is the **operational completion** of Engineering Autopilot, per the [owner-approved roadmap](https://github.com/DaniilSydorenko/.github/issues/207#issuecomment-7231706196). The canonical checklist is [DELIVERY_PLAN_164.md § Operational completion](docs/initiatives/ai-engineering/DELIVERY_PLAN_164.md#operational-completion-checklist). Implementation issues: #226 (queue), #229 (OPS-2 preparation), #230 (OPS-3 autonomous execution), #231 (OPS-4 merge and repair), #232 (OPS-5 multi-repo and private control plane), #233 (OPS-6 control contract and UI), #234 (OPS-7 final acceptance); usage evidence #120.

- **Loop per session:** recover the canonical state once, then implement the highest-priority dependency-ready task with focused regression tests. Run local checks, open a PR, verify exact-head CI, integrate within delegated authority, verify `main`, update the issue and checklist, and **continue to the next eligible task**. Do not stop after one issue, commit or PR.
- **One active implementation writer, serial integration.** Prefer several coherent sequential PRs over one oversized PR. No dependent work on an unaccepted baseline.
- **Owner-only:** paid agent launches, new privileged authorization policies, protected-environment approvals, security or credential changes, new infrastructure, high-risk changes, releases and production deployments, and product decisions that cannot be inferred. Batch these into one request. Asking for throughput is not blanket authorization for them.
- **Confidentiality:** this repository, its refs and its Actions logs are **public**. Never store or log metadata of private repositories here: issue numbers, paths, branches, PRs, SHAs or task text (for example `listing-kit` or `engineering-handbook`).
- **Unchanged:** every security, domain-authority, budget, approval and writer-coordination rule below. Never fabricate evidence; `UNKNOWN` cost stays `UNKNOWN`.

The 2026-11-25 sections below are **historical pilot guidance**, kept for audit. Where they conflict with this section on process (such as "one coherent fix per round"), this section wins. On security and authority they still apply.


## Historical: execution-first mandate for the #164 pilot (2026-11-25, completed)

For the OpenHands #164 pilot, this mandate supersedes conflicting procedural guidance, but never security, owner approval, budget, scope or single-writer controls.

- Every round must implement a known blocker, execute a relevant test, integrate an eligible change, or perform an authorized live run. Status-only rounds are permitted only for a concrete external blocker.
- Read the current PR/head and relevant code once. Do not repeat unchanged audits, inventories, architecture reviews or readiness reports.
- Batch related implementation and regression tests into one coherent commit. Reuse the existing PR and toolchain; avoid new abstractions, services and planning documents.
- Run focused tests and required exact-head CI. A failed test must lead to a fix, not another report. Do not poll unchanged pending checks repeatedly.
- Once required gates pass, integrate promptly within existing merge authority. Request any required owner approval once, with exact PR and HEAD.
- Prefer a real OpenHands run and observable output over additional offline simulations once live prerequisites are satisfied. Never rerun a paid model to repair a deterministic integration defect.
- Keep the current pilot sequential: finish #217 acceptance and lease release before #226. No automatic agent PR merge, bypass, duplicate dispatch or invented evidence.
- Report only the actual code change, test outcome, integration outcome and remaining actionable blocker. Do not claim a test passed merely because it was written.


## Historical: delivery-first pilot override (2026-11-25, completed)

For #164 only, this section supersedes older planning, cadence, delegation-discovery and reporting requirements, not security or domain authority. The current goal is one accepted #217 agent result, not a general orchestration platform.

- One existing implementation PR, one writer, one coherent fix per round. Direct connector edits are the default for bounded HQ fixes; no mandatory Cursor evaluation or paid delegation.
- Read the active PR and relevant code once; implement the complete known blocker in the same round. Do not repeat unchanged audits, status-only rounds, roadmap estimates or create new helpers unless necessary for a working path.
- Reuse the protected workflow, App writer, durable CAS/replay ledger, provider cap, scope validation and required exact-head CI. No new service, scheduler, credential, ruleset or abstraction. Never bypass protections or fabricate acceptance.
- Check only changed dependencies and required gates. Run focused regression tests and existing required CI once per final HEAD; poll only when a result can change the next action. Fresh live authorization and security evidence remain mandatory at execution.
- Recovery is an explicit terminal rejected-result path, not successful integration. Preserve history; prove terminal execution and rejected artifact, then admit at most one bounded correction for #217. No parallel writers or automatic merge.
- Finish #192, recover the lease, execute #217, review the actual snippet and exact-head CI. #226 and all platform expansion are deferred until owner acceptance. Escalate an actual owner-only action once, with exact instructions.
- Report only changed code/PR, test result, actual blocker and next action. If no mutation is possible, state the concrete tool or authority limitation; do not imply progress.


## Mandatory AI engineering delivery bootstrap (proposed in #166)

For work in `docs/initiatives/ai-engineering/**` or `ai-eng-*` workflows, first read [Delivery Governance](docs/initiatives/ai-engineering/DELIVERY_GOVERNANCE.md), then the initiative's canonical delivery plan (currently [#164](docs/initiatives/ai-engineering/DELIVERY_PLAN_164.md)), tracking issue and active PR exact-head CI. Treat these as the **working source of truth across new chats**. Keep owner interaction brief; use bounded AI sessions rather than eight-hour workday estimates. This is process guidance, **not** permission to launch models, alter security or operate other repositories. Existing owner/security/domain gates prevail.


This repository owns shared GitHub HQ infrastructure and governance, **not** domain product backlogs. Start with `reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md`, the canonical `reports/github-hq/ROADMAP-LIVE.md`, and local GRS rules when the task touches GRS. The separate `docs/initiatives/ai-engineering/ROADMAP.md` is an owner research initiative, not HQ enforcement authority. Never alter product repositories, their PR queues, account billing or publication through an HQ issue without the relevant explicit owner/safety gates.

## GitHub HQ integration and AI autonomy boundary (2026-10-26)

GitHub HQ is **infrastructure steward**, not a manager of other repositories' PRs or a second Cursor scheduler. AI Driven Ecosystem exclusively owns `docs/initiatives/ai-engineering/**` and execution semantics of `.github/workflows/ai-eng-*`; HQ only reviews shared GitHub triggers, permissions, secrets, concurrency and protections. Control Plane owns scheduled fleet state; product/domain teams own their merges and releases. Do not rewrite someone else's active branch or create duplicate tracking Issue/PR.

**Finish First:** reconcile accepted `main` against existing HQ issues/PRs, repair proven defects, and close only after exact-head CI, authorized merge and post-merge readback. Documentation updates or owner requests to clear a queue do **not** authorize Class C/security merges, GitHub admin changes, visibility, release, token/account changes or paid agents.

**NO unattended Cursor activation from HQ:** AI Engineering must independently prove a protected singleton lease / sole allowed writer, provider token and billing/BYOK visibility, launch-route controls, owner GO and one measured low-burn Issue/PR → single Cursor run → tests → permitted merge → accepted `main` → safe lease release. Unknown evidence => STOP, not an extra agent or new controller.

## Engineering chat delegation discovery

For an owner-requested engineering implementation, fix, test or code review, **explicitly evaluate GitHub Issue → `@cursor` before defaulting to GitHub Connector-only edits**. Connector is the coordination/evidence tool; a bounded Cursor run is a candidate executor, **not** an automatic entitlement. Follow [Delegation discovery](docs/initiatives/ai-engineering/OPERATING_RULES.md#delegation-discovery--default-for-engineering-chats-manual-owner-gated), local domain authorization, active-writer/provider/budget gates and one-shot dispatch rules. If any gate is unknown, STOP rather than launch. A posted `@cursor` comment is only a request, not proof of agent start. This does not activate unattended Cursor or give HQ authority over product repositories.

## Low-Burn agent work (owner-approved Cursor/Issue tasks)

- Use **one Issue = one coherent, verifiable outcome**. Fetch current default-branch SHA and relevant Issue/PR; read mandatory local rules plus only task-relevant files initially. Expand context only for a proved dependency; do not default to whole-repo or full-chat ingestion.
- Scope one branch/active writer; preserve others' work. No surprise subagents, duplicate agent launches, unrelated refactors, or open-ended retries. Initial implementation + at most **two evidence-based corrections**, then STOP/BLOCKED if no new evidence.
- Require focused tests and all existing exact-head CI/security/quality gates; cost never permits weakening a local 12-step process, review, ownership, safety, privacy, or release approval.
- Keep completion to outcome, PR/HEAD, changed files, CI evidence, blocker/next action. Report **provider-measured** input/output/cache/total tokens and charged cost **only when authorized data is accessible**; otherwise `UNKNOWN`. Do not launch an extra agent just to calculate usage or expose credentials/billing details.
- Central reference (consult only when needed, **not a compulsory large context preload**): https://github.com/DaniilSydorenko/.github/blob/main/docs/initiatives/ai-engineering/OPERATING_RULES.md . This is a **non-enforcing local adoption**, not central HQ permission to operate this product; local/domain rules take precedence.
