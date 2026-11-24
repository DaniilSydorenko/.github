# #164 — Current delivery plan (2026-11-24)

This is the current operational status, not a grant of authority. See [Operating Rules](OPERATING_RULES.md) and [Delivery Governance](DELIVERY_GOVERNANCE.md). Historical baselines, estimates and findings remain in Git history.

## Current objective

One protected OpenHands executor, one active task, one verified Draft PR for Haversine #217. #216 was verified already satisfied (no model invocation). #226 remains blocked until #217 has independently verified exact-head CI/security and the owner-approved continuation gates pass. No agent PR auto-merge. No new scheduler or executor.

## Verified baseline

- HQ #183–#186 integrated the pilot wiring, scoped writer and admission changes.
- [#187](https://github.com/DaniilSydorenko/.github/pull/187) merged at `07d7b8a5a648d4cb2724aa4783b02c76d6f89542`. Its exact pre-merge HEAD `8e39ebd2b4b494c5623bf20509d4d95f93584bdd` passed [Singleton #72](https://github.com/DaniilSydorenko/.github/actions/runs/45411895747) and [Offline #23](https://github.com/DaniilSydorenko/.github/actions/runs/45411895784).
- G3 audit runs on a separate protected job; structured evidence binds repository, SHA, run, attempt, issue and writer App ID. Administrative audit credential is not passed to the live runner. This is implemented and offline-tested, not live-attested.
- Previous real run 45278457105 stopped before model invocation because ruleset details or bypass inventory were hidden. Full authenticated visibility and effective enforcement remain unproved.

| Package | Current status | Remaining acceptance |
|---|---|---|
| D0 launch/writer inventory | PARTIAL | Prove all relevant launch routes and exclusive writer |
| D1 G3 | IMPLEMENTED, LIVE PROOF BLOCKED | Protected audit-only run, authenticated ruleset shape, effective CAS and negative mutation proofs |
| D2 lease/admission | IMPLEMENTED, OFFLINE TESTED | Live enforcement and recovery evidence |
| D3 executor/publisher | IMPLEMENTED for current pilot | Real #217 scoped Draft PR |
| D4 protected workflow | MERGED, OFFLINE TESTED | Main audit-only run and real exact-head evidence |
| D5 G0–G4 | NO-GO FOR LIVE | All applicable gates independently verified and owner GO |
| D6 paid pilot | NOT RUN for #217 | One Draft PR, exact-head CI/security, measured spend and safe lease release |

## Next action

Use the existing protected workflow on main, issue 217, execute_model=false, after verifying the required environment credential is configured by the owner. No model spend. If ruleset inventory is still hidden, report the exact failure and minimum credential decision; do not weaken the gate. A CANDIDATE result is not proof of effective singleton enforcement or live authorization.

Then verify remaining G3/G4 evidence, including provider-enforced shared $1 cap, target scope, collision checks and owner GO before live execution. Do not advance #226 or onboard another project prematurely.

## Execution discipline

One bounded engineering round = one coherent atomic change with focused tests where applicable, expected-head write, readback and exact-head CI. Integration or an operational test may be the concrete outcome without manufacturing a commit. No duplicate PRs, force push, parallel writers, blind retries or filler changes. Preserve separate owner gates for security merges, credentials, permissions, paid execution, releases and deployments. Unknown evidence means STOP. Report implemented, tested, merged and operationally proven separately.
