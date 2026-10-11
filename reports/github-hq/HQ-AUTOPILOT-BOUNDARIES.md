# [CAREER][GITHUB] — HQ / Autopilot Operating Boundaries

Date: 2026-10-11
Status: ACTIVE

## One program, two control views

There is one GitHub program, but there are two intentionally separate roadmaps:

- `reports/github-hq/ROADMAP-LIVE.md` — owned by the synchronous [CAREER][GITHUB] HQ chat.
- `reports/github-autopilot/ROADMAP-2026-10-11.md` — owned by GitHub Autopilot.

Neither worker edits the other's roadmap.

The HQ roadmap is the owner-facing source for full-program status, percentages, newly discovered gaps, owner gates and cross-repository coordination.

The Autopilot roadmap is the execution worker's own operating plan.

## [CAREER][GITHUB] HQ owns

- owner-facing roadmap and milestone status;
- cross-repository strategy and sequencing;
- public/private architecture and publication readiness;
- owner-decision gates;
- repository metadata/profile/pins/topics planning;
- central governance policy;
- safety review of risky merges;
- exact-head verification before synchronous merges;
- triage of new gaps/bugs into the HQ roadmap;
- coordination when repository/domain ownership is ambiguous.

## GitHub Autopilot owns

- bounded scheduled maintenance;
- bounded governance hardening;
- bounded repository-health fixes;
- drift detection;
- preparation of safe PRs inside its allowed surfaces;
- CI/retry diagnostics that do not require owner decisions;
- roadmap execution inside its own operating plan.

## Domain workers own

- Engineering Labs product/training implementation;
- Engineering Handbook authored theory/content;
- Career Intelligence product/data/platform implementation;
- Ladvero product implementation;
- Haversine domain/API evolution when it exceeds repository maintenance/release engineering.

GitHub HQ may audit these repositories for readiness and may perform explicitly authorized maintenance/release-engineering work, but must not silently take over domain ownership.

## Collision rules

Before every mutation:

1. inspect current default branch;
2. inspect open PRs;
3. inspect the exact target branch/head;
4. inspect current CI;
5. inspect whether another worker already changed the same surface;
6. stop, rebase, or choose a different task if ownership or file overlap is unclear.

Never merge an exact head that has changed since verification.

Never force-update a branch without an expected SHA lease.

Never change repository visibility without explicit owner approval.

Never treat a scheduled worker failure as permission to take over its entire domain.

## Roadmap synchronization rule

HQ and Autopilot may report different percentages because they measure different views.

They must agree on factual repository state.

When the HQ discovers a real bug, gap or required task:

- add it to the HQ roadmap as `[NEW]`;
- do not silently expand an old task;
- do not write it into the Autopilot roadmap unless Autopilot itself adopts it.

When Autopilot completes work that changes program state, HQ updates its own roadmap on the next synchronous round after live verification.

## Finish-line rule

Do not create work merely to keep activity going.

A task may be added only when it is required by an existing milestone goal, a discovered safety/correctness defect, or an explicit owner request.

This prevents an endless-roadmap failure mode.
