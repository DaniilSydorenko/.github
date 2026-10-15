# [CAREER][GITHUB] — Independent Live Roadmap

**Owner:** synchronous GitHub HQ. **Reset:** Infrastructure Reset v1, owner-approved 2026-10-15. Accepted truth comes from repository default branches and applicable runtime providers, not from chat status or open PRs.
**Complete pre-reset history:** [immutable original roadmap at commit 37dde39](https://github.com/DaniilSydorenko/.github/blob/37dde39e6311f4c3176f156f8ed2a49ca9cf7fa2/reports/github-hq/ROADMAP-LIVE.md) (742 lines, 101,372 characters, including all task-level estimates and prior updates). No historical evidence or tasks are deleted; this file carries the current view.
**Authority:** [HQ / Autopilot boundaries](HQ-AUTOPILOT-BOUNDARIES.md), [engineering round protocol](ENGINEERING-ROUND-PROTOCOL.md), [GRS](../../grs/OPERATING-MODEL.md), [seven-repository registry](../../governance/repository-registry.json), and separately owned [Autopilot roadmap](../github-autopilot/ROADMAP-2026-10-11.md).
**Core boundary:** infrastructure ready does not mean domain product complete or safe to publish. No change to M4 acceptance scope, existing owner/security gates, or unapproved C01–C07 enforcement.

## Current accepted scoreboard

| Score | Accepted result | Scope |
| --- | --- | --- |
| **Current GitHub scope — full milestone closure** | **7/9 = 77.8%** | M0/M1/M2/M3/M5/M9/M10 accepted; M4 and optional M8 open; M6/M7 deferred, preserved in history. |
| **Governance v1 — full milestone closure** | **4/8 = 50.0%** | GOV-M01/M02/M05/M06 accepted; M03/M04/M07/M08 open. |
| Historical whole-program estimate | 88% (not acceptance) | Unweighted legacy effort score; do not mix domain percentages. |
| Historical governance estimate | 90% (not acceptance) | Not seven-repo operational proof. |

## Execution boundaries and outstanding decisions

- HQ owns GitHub-wide GRS/policies, registry, owner-facing roadmap, cross-repository discovery, and publication/security controls. GitHub Autopilot owns its scheduled execution plan; Control Plane owns fleet/runtime governance. Labs, Handbook, Career Intelligence, LADVERO and Haversine own their code, product/content roadmaps, PR integration and release decisions.
- Do NOT require closing domain PR queues or completing content/product backlogs to accept GitHub infrastructure. Protect local CI and worker permissions. A repository may remain private while engineering proceeds normally.
- [Owner gate #56](https://github.com/DaniilSydorenko/.github/issues/56): proposed binding C01–C07 governance semantics remain unapproved. Registry discovery is not evidence of local enforcement.
- **M4 stays 66% with its original scope** until separately approved owner rescoping. Its domain extraction, history audit and visibility approvals remain unfinished; owner publication approval stays mandatory.
- [HQ PR #82](https://github.com/DaniilSydorenko/.github/pull/82): publication-auditor hardening under independent review at reset baseline; do not infer publication permission from CI or hold unrelated HQ work hostage to its review.
- **M1 stays 100%:** original portfolio Maps key matched exactly to revoked Cloud key; historic PR diff still contains the revoked credential. [Evidence report](M1-GCP-LEGACY-CLEANUP-EVIDENCE-2026-10-14.md) and the preserved original roadmap record owner risk acceptance and later technical correlation. Do not publish key strings.
- Read-only GRS inventory confirmed again 2026-10-15: `.github/repository.json` exists in 1/7 (Haversine); this is discovery evidence, not seven-repo operational PASS. Local-domain CI can remain healthy without new C01–C07 enforcement.
- Live branch safety: all seven branch endpoints return `protected: false`; public `.github`/Haversine ruleset lists are empty, and the five private ruleset reads return GitHub 403/plan restrictions. Required branch protection/review enforcement is therefore **NOT VERIFIED** (do not infer it from green checks). Owner/security gates remain binding policy even when GitHub settings do not prove technical enforcement.
- Actions sample (2026-10-15; latest 100 runs per repo, unequal time windows): **321/700 Help Signal** vs previous **322/700**; by registry order `.github` 54, Control Plane 9, LADVERO 55, Career Intelligence 49, Handbook 55, Labs 67, Haversine 32. Control Plane Reconcile = **74/100**. This is event composition, not a time-normalized rate, cost calculation or demonstrated reduction.
- HQ [main 3e14954](https://github.com/DaniilSydorenko/.github/commit/3e14954ab0645080b0e0b5c8497d9a33d5b7a766) now filters Help Signal `workflow_run` to `main` while keeping schedule/dispatch; regression and main CI passed. Post-fix savings **UNKNOWN**: most of the sampled activity precedes the patch. Other domains still have unfiltered workflow-run triggers; changes remain domain-owned.
- Current open PR inventory (paginated where needed): HQ 1 (security [#82](https://github.com/DaniilSydorenko/.github/pull/82)), Control Plane 0, LADVERO 7, Career Intelligence 7, Handbook 44 (43 Draft), Labs 0, Haversine 0. Open domain PRs are not HQ acceptance blockers. #82 exact-head CI passed; only a COMMENTED review was found, not independent approval.
- Noise causes to investigate within owner scope: workflow-run fan-out from PR CI/secret scans, Help Signal schedule overlap and Handbook cancellation supersession; Control Plane telemetry/reconcile pushes and derived-state writes. Labs/LADVERO historical Help Signal failures are health alerts (exit 1), not yet proof of defective signal code. Actions-minutes and scheduler truth remain UNKNOWN.
- GRS evidence uses PASS / FAIL / UNKNOWN / EXCEPTION. No evidence means UNKNOWN. Routine domain PRs follow locally authorized fast paths; Class C, credentials, visibility, releases, history rewrites and changed exact heads keep their established gates.

## GitHub HQ milestones — canonical acceptance rows

## M0 — Final Forensic Audit
| Task | Color | % |
| --- | --- | ---: |
| M0 — Final Forensic Audit | 🟢 | 100% |

## M1 — Clean & Secure Account
| Task | Color | % |
| --- | --- | ---: |
| M1 — Clean & Secure Account | 🟢 | 100% |

## M2 — Professional GitHub Shell
| Task | Color | % |
| --- | --- | ---: |
| M2 — Professional GitHub Shell | 🟢 | 100% |

## M3 — Public Flagship Wave 1
| Task | Color | % |
| --- | --- | ---: |
| M3 — Public Flagship Wave 1 | 🟢 | 100% |

## M4 — Career Ecosystem Public Extraction
| Task | Color | % |
| --- | --- | ---: |
| M4 — Career Ecosystem Public Extraction | 🔵 | 66% |

M4-A inventory accepted; Labs, Handbook, Career Intelligence extraction, full-history content/PII checks and M4-G visibility approvals remain unaccepted. Original M4-B/C/D/E/F/G subtasks and estimates are preserved in [pre-reset M4 details](https://github.com/DaniilSydorenko/.github/blob/37dde39e6311f4c3176f156f8ed2a49ca9cf7fa2/reports/github-hq/ROADMAP-LIVE.md#M4--career-ecosystem-public-extraction).

## M5 — Haversine OSS Flagship
| Task | Color | % |
| --- | --- | ---: |
| M5 — Haversine OSS Flagship | 🟢 | 100% |

HQ M5 acceptance does not claim the Haversine domain roadmap, beta/stable releases or future API work are complete.

## M8 — Super Profile
| Task | Color | % |
| --- | --- | ---: |
| M8 — Super Profile | 🔵 | 62% |

Optional but retained in the nine-milestone denominator. Pins, metadata/topics, recruiter-first presentation and final visual QA remain.

## M9 — Living Governance
| Task | Color | % |
| --- | --- | ---: |
| M9 — Living Governance | 🟢 | 100% |

Existing GRS base accepted; this is NOT approval of new C01–C07 cross-repository enforcement.

## M10 — GitHub Autopilot
| Task | Color | % |
| --- | --- | ---: |
| M10 — GitHub Autopilot | 🟢 | 100% |

HQ closeout does not replace independently owned Control Plane or scheduled-runtime evidence.

## GOV — Engineering Governance v1

| Task | Color | % |
| --- | --- | ---: |
| GOV-M01 — Baseline Inventory | 🟢 | 100% |
| GOV-M02 — Authority & Conflict Matrix | 🟢 | 100% |
| GOV-M03 — Governance Contract v1 | 🔵 | 92% |
| GOV-M04 — Machine-Readable Baseline | 🔵 | 95% |
| GOV-M05 — Haversine Pilot | 🟢 | 100% |
| GOV-M06 — Seven-Repository Adoption | 🟢 | 100% |
| GOV-M07 — Automated Validation | 🔵 | 84% |
| GOV-M08 — Acceptance & Freeze | 🔵 | 58% |

M05/M06 close pilot and *discovery mapping*, NOT full fleet operational validation. M03/M04 require owner decisions; M07 needs observed evidence (not only an all-UNKNOWN test); M08 requires explicit operational acceptance and architecture freeze.

## Infrastructure Reset v1 — five bounded rounds (approved 2026-10-15)

| Round | Deliverable | Evidence and gate |
| --- | --- | --- |
| R1 — Compact live roadmap / authority | ≤150 lines and ≤15 KiB; preserved Git history; parser tests; additive HQ scope clarification | Exact-head CI, permitted review/integration, remote-main verification |
| R2 — Minimal contract | Reconcile already-active GRS/discovery, advisory C01–C07 vocabulary and genuinely proposed required controls under [#56](https://github.com/DaniilSydorenko/.github/issues/56); avoid duplicate rules | No new binding enforcement without explicit owner authorization |
| R3 — Safe fast path | Reuse existing local CI and approved bounded worker merges; eliminate repetitive HQ gatekeeping | Demonstrate low-risk autonomous path and Class C fail-closed safety |
| R4 — Seven-repo evidence | Existing GRS reporter, live observed discovery/class/CI/operational evidence | PASS/FAIL/UNKNOWN/EXCEPTION per repo; no dependence on domain PR completion |
| R5 — Optimize / accept / freeze | Measure and reduce avoidable Actions churn; verify safety and governance closure | Owner-approved gates, no invented acceptance, stop building mechanics |

**Stop rules:** one genuine owner/security blocker is recorded once; continue elsewhere without changing domain ownership. No new database, service, dashboard, scheduler, duplicated status tracker, or inferred green check.

## Historical access and handoff

- [Full pre-reset 2026-10-14 roadmap](https://github.com/DaniilSydorenko/.github/blob/37dde39e6311f4c3176f156f8ed2a49ca9cf7fa2/reports/github-hq/ROADMAP-LIVE.md) is an immutable Git-commit reference, preserving 100% of old narrative, detailed tasks, evidence links and historical decisions without creating another giant file.
- [M1 evidence](M1-GCP-LEGACY-CLEANUP-EVIDENCE-2026-10-14.md) · [governance draft](../../governance/ENGINEERING-GOVERNANCE-V1-DRAFT.md) · [registry](../../governance/repository-registry.json). M6/M7 remain deferred, not cancelled or earned.
- When the infrastructure satisfies its approved exit gates, stop expanding governance and return to low-churn maintenance.
