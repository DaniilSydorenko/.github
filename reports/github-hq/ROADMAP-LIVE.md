# [CAREER][GITHUB] — Independent Live Roadmap

**Owner:** GitHub HQ. **Strategy:** Infrastructure Reset v1 (2026-10-15). Accepted code = default branches; runtime = actual provider. **Historical record:** [immutable pre-reset roadmap](https://github.com/DaniilSydorenko/.github/blob/37dde39e6311f4c3176f156f8ed2a49ca9cf7fa2/reports/github-hq/ROADMAP-LIVE.md). No second archive.
**Authority:** [HQ boundaries](HQ-AUTOPILOT-BOUNDARIES.md) · [round protocol](ENGINEERING-ROUND-PROTOCOL.md) · [GRS](../../grs/OPERATING-MODEL.md) · [registry](../../governance/repository-registry.json) · [owner gate #56](https://github.com/DaniilSydorenko/.github/issues/56). Domain roadmaps and Control Plane remain independent.

## Current accepted scoreboard

| Score | Accepted result | Scope |
| --- | --- | --- |
| **Current GitHub scope — full milestone closure** | **7/9 = 77.8%** | M0/M1/M2/M3/M5/M9/M10 closed; M4/M8 open. M6/M7 deferred in Git history. |
| **Governance v1 — full milestone closure** | **8/8 = 100.0%** | Owner-approved **lean non-enforcing** C01–C07, existing GRS/discovery/read-only validation, observed local CI and documented exceptions. NOT universal fleet operational PASS. |

## Governance v1 — ACCEPTED / FROZEN within Option B scope

- [Issue #56](https://github.com/DaniilSydorenko/.github/issues/56) **closed with explicit owner Option B** on 2026-10-15: new binding C01–C07 enforcement, forced seven-repo manifests, agent-file templates, status databases, dashboards and mandatory fleet CI are **not planned**. Existing GRS/default-deny/local CI/security/owner gates remain. No implicit authority expansion.
- [Lean contract](../../governance/ENGINEERING-GOVERNANCE-V1-DRAFT.md) · [GRS tests](../../grs/tests/) · [read-only drift audit](../../grs/audit_repository_registry_drift.py) · [fleet evidence reporter](../../grs/report_fleet_conformance.py). The legacy filename is preserved to avoid path churn; Git history preserves former text.
- **Observed discovery proof:** 35/35 registered pointer paths exist in seven complete default-branch Git trees (2026-10-15). **Local CI evidence (2026-10-15 checkpoint):** 7/7 sampled default-branch SHAs had successful repository-specific CI. The branches can advance; this historical snapshot is not a live health assertion or proof of worker schedules, releases, branch protections or GRS enforcement.
- **Owner-approved exceptions / nonrequirements:** only Haversine has an active local `.github/repository.json`; other six are not required to adopt one. Class-profile/worker policy-consumption/runtime evidence is UNKNOWN when not observed, never fabricated PASS. No profile or archived-repo forced rollout.
- **Repeatable bounded engineering evidence:** Haversine pilot [#150](https://github.com/DaniilSydorenko/haversine-geolocation/pull/150) and reconciliation #151; HQ compact reset [#87](https://github.com/DaniilSydorenko/.github/pull/87); HQ lean CI+contract [#90](https://github.com/DaniilSydorenko/.github/pull/90), exact-head and post-merge GRS green. [Overhead acceptance](../governance-v1/GOV-M08-OVERHEAD-COST-ACCEPTANCE-2026-10-12.md): no new service, scheduler or status store.
- **Freeze:** no Governance v2 or new mandatory controls absent a separately evidenced recurring safety defect and new owner authorization. Governance 100% means accepted **bounded design and validation**, not that every independent repository, scheduler or GitHub account configuration is fully compliant.

## Independent infrastructure risks / next actions (not GOV reopening)

- **Branch protections:** seven branch endpoints returned `protected: false`; public HQ/Haversine ruleset lists empty, private ruleset inspection hit GitHub plan/API restrictions. Native enforced branch review is **NOT VERIFIED**; this is a real security-review item for the owner, not owner acceptance of bypass. Existing policy/review gates stay binding.
- **Publication:** [HQ PR #82](https://github.com/DaniilSydorenko/.github/pull/82) has exact-head GRS SUCCESS but still needs independent appropriate review. Do not weaken it, publish sensitive content or use it to block independent CI v1 development.
- **M4 stays 66% with its original scope**; domain extraction, history/PII review and owner visibility decisions remain separate. Career Intelligence first private product version does NOT depend on M4 public release.
- **Noise:** latest 100 runs per repo sample yielded 320/700 Help Signal; Control Plane Reconcile 74/100 (unequal time windows, NOT a normalized cost/savings measure). HQ `3e14954` filters PR-triggered health fan-out; longer-term effect UNKNOWN. Optimize only proved redundancy inside each domain authority; never disable security/scheduler blindly.
- **Control Plane-specific unresolved execution:** [Career scheduler bootstrap #152](https://github.com/DaniilSydorenko/autopilot-control-plane/issues/152) and [Career executor write block #160](https://github.com/DaniilSydorenko/autopilot-control-plane/issues/160) were open at the 2026-10-15 audit. Their live state belongs to Control Plane/executor and must be reread there; no duplicate scheduler, unconditional retries or HQ product takeover.
- **Domain autonomy:** open LADVERO/Career/Handbook application PRs are not HQ governance gates. GitHub Autopilot and Control Plane keep their own scheduling/merge authority; synchronous HQ cannot borrow it.

## GitHub HQ milestones — canonical acceptance rows

## M0 — Final Forensic Audit
| Task | Color | % |
| --- | --- | ---: |
| M0 — Final Forensic Audit | 🟢 | 100% |

## M1 — Clean & Secure Account
| Task | Color | % |
| --- | --- | ---: |
| M1 — Clean & Secure Account | 🟢 | 100% |

Legacy **original portfolio Maps key matched exactly** to revoked credential; residual historical exposure recorded with **owner risk acceptance** in [M1 evidence](M1-GCP-LEGACY-CLEANUP-EVIDENCE-2026-10-14.md). Never reproduce key strings.

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

## M5 — Haversine OSS Flagship
| Task | Color | % |
| --- | --- | ---: |
| M5 — Haversine OSS Flagship | 🟢 | 100% |

HQ M5 closure is not Haversine product/release completion.

## M8 — Super Profile
| Task | Color | % |
| --- | --- | ---: |
| M8 — Super Profile | 🔵 | 62% |

## M9 — Living Governance
| Task | Color | % |
| --- | --- | ---: |
| M9 — Living Governance | 🟢 | 100% |

## M10 — GitHub Autopilot
| Task | Color | % |
| --- | --- | ---: |
| M10 — GitHub Autopilot | 🟢 | 100% |

## GOV — Engineering Governance v1

| Task | Color | % |
| --- | --- | ---: |
| GOV-M01 — Baseline Inventory | 🟢 | 100% |
| GOV-M02 — Authority & Conflict Matrix | 🟢 | 100% |
| GOV-M03 — Governance Contract v1 | 🟢 | 100% |
| GOV-M04 — Machine-Readable Baseline | 🟢 | 100% |
| GOV-M05 — Haversine Pilot | 🟢 | 100% |
| GOV-M06 — Seven-Repository Adoption | 🟢 | 100% |
| GOV-M07 — Automated Validation | 🟢 | 100% |
| GOV-M08 — Acceptance & Freeze | 🟢 | 100% |

GOV-M06 = **discovery adoption only**. M07 = existing read-only validator/reporter and real pointer/CI proof, **not mandatory all-repo enforcement**. M08 = owner-approved scoped freeze with explicit exceptions and UNKNOWNs, **not fleet/scheduler readiness certification**.

## Infrastructure Reset v1 — bounded continuation

- **R1:** compact roadmap and authority — ACCEPTED [#87](https://github.com/DaniilSydorenko/.github/pull/87).
- **R2:** minimal non-enforcing governance, CI coverage repair and owner Option B — ACCEPTED [#90](https://github.com/DaniilSydorenko/.github/pull/90) + #56 + this freeze.
- **R3:** safe fast path — reuse existing bounded Class A/B and local CI; domain-owned proof, no universal worker or centralized approvals.
- **R4:** seven-repo discovery/CI proof — ACCEPTED for that **limited observed scope**, not full operational GRS PASS.
- **R5:** governance frozen; any Actions cost optimization and branch security review stay **separate bounded maintenance**, no recurring new governance roadmap.

**Next priority:** first **private** Career Intelligence v1 via the domain-owned [PLATFORM roadmap](https://github.com/DaniilSydorenko/career-intelligence/blob/main/docs/PLATFORM_ROADMAP_V2.md); do not copy its mutable percentages into HQ. No dependency on public-extraction M4, Handbook completion or other-domain PR queues. Stop enlarging governance.
