# #164 Delivery plan — baseline 2026-11-18

**Owner-facing delivery contract, not a claim of live readiness.**
Source of scope: central issue #164. Implementation: existing Draft PR #166.
No new parallel implementation PRs or duplicate Haversine issues.

## Definition of done

One owner-triggered protected workflow attempts Haversine #216 → #217 → #226,
one agent globally, one shared provider-enforced $1 cap, independently
verified Draft PR per issue with exact-head CI/security before transition.
Any uncertainty STOPs; no auto-merge/release/deploy. Offline tests alone do
not satisfy acceptance.

## Planning assumptions and dates

Estimates are **engineering effort, not elapsed calendar promises**.
Assume one focused engineer, GitHub API/config access and no new provider
permissions. Baseline starts 2026-11-18. Dates are provisional checkpoints,
reforecast on newly discovered evidence; no unattended background work
is implied.

| ID | Priority | Work package | Estimate | Target checkpoint | Exit evidence | Status |
|---|---|---|---|---|---|---|
| D0 | P0 | Freeze scope, trace all launch/writer paths, risk register | 0.5–1 day | Nov 19 | Enumerated path inventory + unknowns; explicit no-live decision | IN PROGRESS |
| D1 | P0 | Audit effective lease ruleset, app identity, ref mutation/deletion/non-FF, credential exposure | 0.5–1.5 days | Nov 20 | Authenticated read-only evidence; owner decision if permissions must change | BLOCKED ON PROOF |
| D2 | P0 | Trusted lease adapter and pre-model admission; reuse CAS/replay | 1–2 days | Nov 24 | Negative tests: races, crash, stale ref, double launch, unknown identity | NOT STARTED |
| D3 | P0 | Parameterize #220 executor, verifier, publisher to exact three issue/path contracts | 1–2 days | Nov 26 | Offline E2E proves 3 isolated artifacts, correct paths, no duplicate PR | NOT STARTED |
| D4 | P0 | Protected workflow wiring + exact-head CI/security + release policy | 1–2 days | Nov 30 | E2E failure drills and authenticated no-model preflight | NOT STARTED |
| D5 | P0 | G0–G4 evidence review and owner GO/NO-GO | 0.5–1 day | Dec 2 | Every gate independently PASS or explicit BLOCKED | NOT STARTED |
| D6 | P0 | Owner-authorized bounded paid pilot | 0.5–1 day | Dec 3 (conditional) | 3 verified Draft PRs OR bounded STOP, shared spend cap | NOT AUTHORIZED TO RUN NOW |

**Total estimated engineering effort:** 5–10 working days, excluding
permission review delays, CI queues and unknown defects. The Dec 3 date
is a **conditional planning target**, not a committed completion date.
Confidence LOW until D0/D1 finish. Re-estimate at D1 exit; never hide
schedule changes.

## Current delivered work (in PR #166, not main)

- Read-only authenticated issue/PR inventory with hard STOP.
- G0/G1 fast gate integrated into PR CI, including singleton/CAS regression.
- Offline lease preconditions for issue identity, owner, state and pinned SHA.
- AST triage flags the legacy model path; does NOT block it at runtime.
- Readiness contract G0–G4. Latest CI run must be checked by exact SHA.

## Known blockers — baseline register (not exhaustive)

| Risk | Severity | Evidence/impact | Owner/action | Gate |
|---|---|---|---|---|
| B01 | CRITICAL | No proved global exclusive writer across OpenHands, Cursor, Actions and external launch routes | D0/D1 inventory + owner security review | G3 |
| B02 | CRITICAL | Lease ruleset writer integration/bypass and disabled immutable ruleset need effective verification | D1; do not mutate rules without owner approval | G3 |
| B03 | CRITICAL | #220 runner calls model without trusted lease integration | D2 | G2 |
| B04 | HIGH | Existing runner/verifier/publisher hardcoded to #220 | D3 | G2 |
| B05 | HIGH | No live sequential controller and verified Draft PR transitions | D4 | G2/G4 |
| B06 | HIGH | Shared $1 cap needs fresh provider attestation and per-task remaining budget checks | D4/D5 | G3/G4 |
| B07 | HIGH | Exact-head CI/security and crash/replay recovery not proved end-to-end | D2/D4 | G2 |
| B08 | MEDIUM | Legacy #220 scheduled discovery failure and old/new docs risk operational confusion | D0; isolate legacy route | G0/G3 |

**Known baseline:** 8 risk entries; **not** a claim that only eight
blockers exist. Unknowns are tracked separately until D0 closes.
New P0/P1 findings require issue/PR comment, severity, owner, acceptance
test and impact on dates; never silently expand scope.

## Operating cadence

1. Before code: verify latest PR HEAD, exact CI, D0/D1 dependencies and
   existing PR/issue ownership. No speculative new modules.
2. Each small commit: G0/G1 fast gate; include exact SHA and CI run link.
3. For lease/execution changes: G2 offline integration + negative tests.
4. At D1/D5 and immediately before live: authenticated G3/G4 evidence.
5. Daily owner-facing update when actively working: DONE, IN PROGRESS,
   BLOCKED, newly discovered risks, next milestone and changed forecast.
6. A blocker with no safe local resolution is escalated once for owner
   decision, not repeatedly investigated or bypassed.
7. No merge, paid invocation, secret/ruleset/permission changes or
   deployment without the applicable separate owner authorization.

## Immediate next deliverable

**D0/D1 audit**, not more isolated validation helpers. Enumerate all
model entrypoints, all lease writers, all credentials and GitHub rules
affecting the actual ref. Produce an evidence-backed GO/NO-GO for D2.
