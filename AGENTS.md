# GitHub HQ — agent entry point

This repository owns shared GitHub HQ infrastructure and governance, **not** domain product backlogs. Start with `reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md`, the canonical `reports/github-hq/ROADMAP-LIVE.md`, and local GRS rules when the task touches GRS. The separate `docs/initiatives/ai-engineering/ROADMAP.md` is an owner research initiative, not HQ enforcement authority. Never alter product repositories, their PR queues, account billing or publication through an HQ issue without the relevant explicit owner/safety gates.

## Low-Burn agent work (owner-approved Cursor/Issue tasks)

- Use **one Issue = one coherent, verifiable outcome**. Fetch current default-branch SHA and relevant Issue/PR; read mandatory local rules plus only task-relevant files initially. Expand context only for a proved dependency; do not default to whole-repo or full-chat ingestion.
- Scope one branch/active writer; preserve others' work. No surprise subagents, duplicate agent launches, unrelated refactors, or open-ended retries. Initial implementation + at most **two evidence-based corrections**, then STOP/BLOCKED if no new evidence.
- Require focused tests and all existing exact-head CI/security/quality gates; cost never permits weakening a local 12-step process, review, ownership, safety, privacy, or release approval.
- Keep completion to outcome, PR/HEAD, changed files, CI evidence, blocker/next action. Report **provider-measured** input/output/cache/total tokens and charged cost **only when authorized data is accessible**; otherwise `UNKNOWN`. Do not launch an extra agent just to calculate usage or expose credentials/billing details.
- Central reference (consult only when needed, **not a compulsory large context preload**): https://github.com/DaniilSydorenko/.github/blob/main/docs/initiatives/ai-engineering/OPERATING_RULES.md . This is a **non-enforcing local adoption**, not central HQ permission to operate this product; local/domain rules take precedence.
