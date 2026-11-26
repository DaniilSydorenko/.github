# #164 — High-quality engineering agent (2026-11-26)

Operational roadmap; not a grant of authority. Preserve [Operating Rules](OPERATING_RULES.md) and [Delivery Governance](DELIVERY_GOVERNANCE.md). Supersedes the historical delivery-first pilot plan.

## Baseline

The documentation pilot reached #226 acceptance. Protected run #17 produced Haversine Draft PR #233 for issue #232; its main CI failed. This proves delivery, not code quality. HQ #198 is merged; HQ #199 has passing offline CI but remains draft and lacks real container evidence. Existing #232 lease must not be bypassed.

## Critical path

1. **Validate before publishing.** Finish existing HQ #199: trusted dependency image, real isolated smoke, exact candidate binding, bounded typecheck/test/build/quality commands. Integrate only after required CI. No credentials in candidate execution.
2. **Repair rather than publish broken code.** Extend the existing runner and executor, not a new orchestration system. Provide concise failing diagnostics to the same agent, preserve scope and base, revalidate each candidate, allow at most three total attempts under the existing provider cap. Exhaustion stops without publishing. Reuse the existing PR and lease only through an authorized exact-head repair transition.
3. **Improve engineering context.** Supply repository instructions, relevant implementation and tests, explicit issue acceptance criteria, existing conventions, minimal diff and regression expectations. Require semantic review, not merely green checks. Change the model only if observed failures justify it.
4. **Prove the cycle.** Repair Haversine #233 for #232: finite extreme radius, first-candidate selection, existing tie/validation/API behavior, scoped regression. Exact-head required CI and owner acceptance. Then evaluate five small representative tasks sequentially (bug, edge case, refactor, integration, regression). Record first-pass and final pass, human rework, cost and scope violations in existing PR evidence.

## Acceptance target

All published candidates pass independent required checks on the exact candidate; zero scope/security violations; at least four of five representative tasks accepted without human code edits; no regression or weakened tests; bounded attempts and spend. This small sample is a pilot target, not a statistical guarantee. Human review remains required.

## Execution discipline

One writer, one active task, minimal changes, existing PRs first, exact-head CI, no duplicate manual audits. Merge low-risk changes through existing gates; preserve owner approval for security, credentials, paid execution, release and deployment. No new platform, dashboard, scheduler, agent fleet, generalized retry engine or model benchmarking project. Distinguish implemented, tested, merged and operationally proven.
