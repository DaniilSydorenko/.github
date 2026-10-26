# GitHub HQ — agent entry point

This repository owns shared GitHub HQ infrastructure and governance, **not** domain product backlogs. Start with `reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md`, the canonical `reports/github-hq/ROADMAP-LIVE.md`, and local GRS rules when the task touches GRS. The separate `docs/initiatives/ai-engineering/ROADMAP.md` is an owner research initiative, not HQ enforcement authority. Never alter product repositories, their PR queues, account billing or publication through an HQ issue without the relevant explicit owner/safety gates.

## GitHub HQ integration and AI autonomy boundary (2026-10-26)

GitHub HQ is **infrastructure steward**, not a manager of other repositories' PRs or a second Cursor scheduler. AI Driven Ecosystem exclusively owns `docs/initiatives/ai-engineering/**` and execution semantics of `.github/workflows/ai-eng-*`; HQ only reviews shared GitHub triggers, permissions, secrets, concurrency and protections. Control Plane owns scheduled fleet state; product/domain teams own their merges and releases. Do not rewrite someone else's active branch or create duplicate tracking Issue/PR.

**Finish First:** reconcile accepted `main` against existing HQ issues/PRs, repair proven defects, and close only after exact-head CI, authorized merge and post-merge readback. Documentation updates or owner requests to clear a queue do **not** authorize Class C/security merges, GitHub admin changes, visibility, release, token/account changes or paid agents.

**NO unattended Cursor activation from HQ:** AI Engineering must independently prove a protected singleton lease / sole allowed writer, provider token and billing/BYOK visibility, launch-route controls, owner GO and one measured low-burn Issue/PR → single Cursor run → tests → permitted merge → accepted `main` → safe lease release. Unknown evidence => STOP, not an extra agent or new controller.

## Low-Burn agent work (owner-approved Cursor/Issue tasks)

- Use **one Issue = one coherent, verifiable outcome**. Fetch current default-branch SHA and relevant Issue/PR; read mandatory local rules plus only task-relevant files initially. Expand context only for a proved dependency; do not default to whole-repo or full-chat ingestion.
- Scope one branch/active writer; preserve others' work. No surprise subagents, duplicate agent launches, unrelated refactors, or open-ended retries. Initial implementation + at most **two evidence-based corrections**, then STOP/BLOCKED if no new evidence.
- Require focused tests and all existing exact-head CI/security/quality gates; cost never permits weakening a local 12-step process, review, ownership, safety, privacy, or release approval.
- Keep completion to outcome, PR/HEAD, changed files, CI evidence, blocker/next action. Report **provider-measured** input/output/cache/total tokens and charged cost **only when authorized data is accessible**; otherwise `UNKNOWN`. Do not launch an extra agent just to calculate usage or expose credentials/billing details.
- Central reference (consult only when needed, **not a compulsory large context preload**): https://github.com/DaniilSydorenko/.github/blob/main/docs/initiatives/ai-engineering/OPERATING_RULES.md . This is a **non-enforcing local adoption**, not central HQ permission to operate this product; local/domain rules take precedence.
