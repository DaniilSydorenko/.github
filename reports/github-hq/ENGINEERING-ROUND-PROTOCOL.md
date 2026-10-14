# GitHub HQ — Engineering Round Protocol (Pilot)

Status: **HQ FINISH-FIRST PROCEDURE / NON-ENFORCING FOR DOMAIN WORKERS**. Owner: synchronous GitHub HQ. Scope: HQ engineering rounds; no change to Autopilot or domain-worker authority. This is a reusable runbook, **not** a second task-status store, scheduler or cross-repository policy approval. Governance C01–C07 owner gate #56 remains in force.

## Canonical sources

- Repository discovery: `governance/repository-registry.json`
- Owner-facing milestones: `reports/github-hq/ROADMAP-LIVE.md`
- Authority: `reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md`
- GRS: `grs/OPERATING-MODEL.md`
- Accepted code: repository default branch; proposals: open PR heads; external runtime/scheduler: its own live provider.
- Do **not** copy mutable percentages, PR states or CI results into this protocol.

## Round sequence

1. **DISCOVERY** — fetch fresh default-branch SHA, local canonical roadmap/authority/agent guidance through registry, relevant issues, all open PRs with *paginated* changed-file lists, exact-head CI, and runtime/release evidence if relevant. Note unavailable surfaces.
2. **RECONCILIATION** — compare current GitHub evidence to roadmap claims, separate accepted main state from draft proposals, detect stale or conflicting assertions.
3. **PLANNING** — FINISH-FIRST: inspect already-tested open PRs and existing milestone exit gates before creating work. Choose the smallest bounded closeout set with stable IDs, dependencies and explicit owners; no artificial milestone inflation.
4. **DESIGN** — specify expected changed paths, allowed scope, exclusions, risk, rollback, acceptance criteria and stop conditions.
5. **IMPLEMENTATION** — mutate only authorized paths on a dedicated branch after a fresh collision check. Never modify another worker's branch or roadmap.
6. **VALIDATION** — run applicable tests, security/GRS checks and diff review; disclose tests that cannot be executed.
7. **PR REVIEW** — compare *all* open PR changed paths again. Shared lockfiles, generated manifests and canonical status files are coordination hotspots. A shared path is a collision risk, **not automatically** a Git merge conflict.
8. **EXACT-HEAD CI** — verify required checks for the precise immutable PR HEAD; no checks found is **UNKNOWN**, not PASS. A head change invalidates earlier evidence.
9. **INTEGRATION OR BLOCKED** — accept only with verified current-run authorization, fresh no-overlap/ownership evidence, verified required CI and immutable expected head. A worker's own standing Class A/B approval can qualify only under the exact restrictions in `HQ-AUTOPILOT-BOUNDARIES.md`; synchronous HQ cannot inherit it. Otherwise report the exact OWNER_DECISION or EXTERNAL_BLOCKED and switch independent lanes. Do not bypass owner gates or enforce unapproved C01–C07.
10. **POST-INTEGRATION AUDIT** — inspect default-branch accepted artifact and commit; check deployment/release/runtime separately when applicable.
11. **ROADMAP SYNC** — only the canonical roadmap owner updates their own roadmap, with linked evidence; no progress increase from draft PR alone.
12. **HANDOFF** — report task IDs, outcomes (DONE/BLOCKED/DEFERRED), links, exact SHAs, CI, unresolved collisions, risks and next bounded work.

## Task execution contract (use in PR/Issue or round notes, not a new database)

- **ID / owner / repository / canonical source**
- **Goal and user-visible value**
- **Dependencies and touched paths / explicitly excluded paths**
- **Risk / security and owner approval gates / rollback**
- **Acceptance and exact-head validation evidence**
- **Stop conditions / retry budget**
- **Outcome and post-merge/runtime verification when applicable**

## Finish-first exit discipline

- Reuse the active `reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md` **Finish-first closeout contract**; no parallel policy or status database.
- Each engineering round must select an **existing unfinished acceptance gate or tested PR** before starting new governance work. If all eligible work needs owner decisions, prepare one bounded batch; don't create compensating reports.
- After two equivalent failures without new information, **stop equivalent retries** and work on a non-colliding owned lane or return a precise single owner decision.
- The only successful engineering closeout is **ACCEPTED** on a remotely verified canonical branch (and runtime/release evidence where originally required). **OWNER_DECISION**, **EXTERNAL_BLOCKED**, and **CONTINUE_ELSEWHERE** are truthful outcomes, not 100% completion.
- No new milestones, scheduled workers, duplicated status trackers, forced seven-repo enforcement or weakened owner gate #56. Freeze the existing scope and denominator.

## Pilot acceptance checklist

- [ ] A real scoped task selected from live sources, with evidence-backed baseline
- [ ] Full target-repository open-PR path collision audit completed before mutation
- [ ] Implementation isolated to its declared paths; no owner-boundary expansion
- [ ] Relevant tests and exact-head CI independently verified
- [ ] Either safely integrated and checked on default branch, or explicitly blocked with reason
- [ ] Only the correct roadmap owner updates status after acceptance
- [ ] Handoff records next action without claiming unverified completion

## Explicit safety constraints

- An open PR is *implemented/proposed*, not *merged*; a green PR CI is *tested*, not *deployed*.
- No new DB, dashboard, scheduler, webhook, bot or mandatory cross-repository CI.
- No credentials, visibility changes, destructive history edits or publication without owner approval.
- No silent domain takeover, no auto-merge on missing checks, no percent inflation.
- If this protocol adds more maintenance cost than proven value, simplify or stop.
