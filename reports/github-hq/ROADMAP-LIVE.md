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

- **Branch security:** HQ `main` currently `protected:false`, rulesets `[]` — owner/admin [#108](https://github.com/DaniilSydorenko/.github/issues/108). Target **main only**; no globally required path-filtered checks or unverified bypass. Separately, AI Engineering's `ai-eng-cursor-lease-v1` is also unprotected and requires a DIFFERENT protected single-writer fast-forward/CAS rule (AI #120 / PR #133); never apply main's PR-only rule to it.
- **Publication:** HQ [PR #82](https://github.com/DaniilSydorenko/.github/pull/82), exact-head GRS 136/136 PASS at `0bf2206`, remains OPEN without independent security approval. Private/public gate remains closed.
- **M4 stays 66% with its original scope**; owner-directed sequencing on 2026-10-15 is **PUBLICATION DEFERRED / KEEP PRIVATE**, not M4 delivery accepted or 100%. Domain extraction, history/PII review and explicit owner visibility decisions remain separate. Career Intelligence first private product version and M8 profile polish do NOT depend on M4 public release.
- **Actions health:** HQ #109 CLOSED `NO_READY_WORK` for unproven billable CI waste. Different correctness defect fixed in [PR #136](https://github.com/DaniilSydorenko/.github/pull/136), MERGED `4337635e` 2026-10-26: exact-head 111/111 PASS, post-merge GRS and live HQ Help Signal SUCCESS. Not proof of fleet-wide rollout or financial savings.
- **Control Plane latest snapshot (2026-10-26 10:04 UTC):** [canonical state](https://github.com/DaniilSydorenko/autopilot-control-plane/blob/main/state/latest.json) Manager **GREEN**; Ladvero scheduled worker **DISABLED** despite GREEN health classification. The Oct 21 YELLOW report is historical. Scheduler and worker authority stay with CP.
- **Domain autonomy:** open LADVERO/Career/Handbook application PRs are not HQ governance gates. GitHub Autopilot and Control Plane keep their own scheduling/merge authority; synchronous HQ cannot borrow it.

## HQ issue execution map (GitHub/Cursor handoff, 2026-10-23)

- **[M8 final profile acceptance #107](https://github.com/DaniilSydorenko/.github/issues/107):** post-#12 real iPhone QA and owner-approved repository metadata remain. Owner **deferred website/DNS** on 2026-10-25; not acceptance or a blocker for other infrastructure. No speculative DNS retries.
- **[R5 branch protection #108](https://github.com/DaniilSydorenko/.github/issues/108):** read-only feasibility/minimal settings; actual enforcement requires owner authorization and provider readback.
- **[R5 Actions cost #109](https://github.com/DaniilSydorenko/.github/issues/109):** CLOSED `NO_READY_WORK` after verifying public HQ standard-runner pricing and healthy workflows; no unsafe CI optimization, no claims about private-repo billing.
- **M4 security:** existing [PR #82](https://github.com/DaniilSydorenko/.github/pull/82) is the live review artifact, independent approval outstanding; broader M4 publication remains **DEFERRED / KEEP PRIVATE**. No new M4 agent task, no automatic Cursor launch. Completed M0–M3/M5/M9/M10 and GOV do not need replay Issues.
- [AI Engineering](../../docs/initiatives/ai-engineering/ROADMAP.md) stays owner-led and separate. **Low-Burn guidance 7/7 in default branches**: [central #113](https://github.com/DaniilSydorenko/.github/pull/113), [HQ #114](https://github.com/DaniilSydorenko/.github/pull/114), [six domain merges](https://github.com/DaniilSydorenko/.github/pull/113#issuecomment-6368213761). Offline [gate #112](https://github.com/DaniilSydorenko/.github/pull/112) accepted as advisory only. **Real Cursor token/cost proof OPEN [#120](https://github.com/DaniilSydorenko/.github/issues/120)**; no savings or runtime enforcement claimed. HQ owns HQ percentages only.

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

Publication remains deferred for Labs, Handbook and Career Intelligence. Original M4 security, current-tree/history, domain extraction and owner visibility gates remain OPEN; [security PR #82](https://github.com/DaniilSydorenko/.github/pull/82) requires independent approval. No visibility change or new repository, and no transfer of domain PR authority to HQ.

## M5 — Haversine OSS Flagship
| Task | Color | % |
| --- | --- | ---: |
| M5 — Haversine OSS Flagship | 🟢 | 100% |

**HQ M5 closure does not grant domain release authority.** Stable [Haversine v2.0.1](https://github.com/DaniilSydorenko/haversine-geolocation/releases/tag/v2.0.1) published 2026-10-25, non-prerelease. Older beta/staging failures are historical, not the latest release. npm/release/code remain Haversine-owned.

## M8 — Super Profile
| Task | Color | % |
| --- | --- | ---: |
| M8 — Super Profile | 🔵 | 95% |

**Accepted on GitHub default branch:** [profile PRs #8](https://github.com/DaniilSydorenko/DaniilSydorenko/pull/8), [#9](https://github.com/DaniilSydorenko/DaniilSydorenko/pull/9), [#10](https://github.com/DaniilSydorenko/DaniilSydorenko/pull/10), [#11](https://github.com/DaniilSydorenko/DaniilSydorenko/pull/11) and **[#12](https://github.com/DaniilSydorenko/DaniilSydorenko/pull/12)**. Profile `main` `d9d17a1`, exact-head and post-merge GRS Governance + Secret Scan SUCCESS. Positioning, Klarna/Allegro commercial evidence, public Haversine GitHub v2 beta, governance, privacy boundaries and responsive hero are retained; no product or domain PR takeover.

**2026-10-17 owner GitHub Safari screenshots — visual evidence:** profile account role, real GitHub-rendered **mobile hero**, links, recruiter-first text and private/public labels are legible; public pinned cards show **Haversine first and `.github` second**, as configured in the earlier editor screenshot. **One actual mobile defect was found:** `Selected engineering work` four-column table clipped Status and `What I build` forced narrow 50/50 columns. PR #12 replaced only those two layouts with natural-width Markdown sections/lists, preserved the source facts, all six projects and URLs; remote `main` confirms no affected HTML/wide table remains. **Post-fix GitHub-mobile rendering not yet independently accepted**; the prior iPhone screenshots predate PR #12. **2026-10-17 owner desktop GitHub screenshots after PR #12: DESKTOP VISUAL QA ACCEPTED** — recruiter-first first screen, readable four stacked What I build sections, six readable Selected engineering work list entries with intact status, profile roles/links, and both pinned repository cards in correct order. No clipped four-column work table in the actual desktop renderer.

**Remaining M8 closeout gates:** (1) post-PR-#12 real iPhone QA for `What I build` and `Selected engineering work`; (2) owner-approved profile repository description and domain-approved Haversine V2 metadata; (3) website verification **deferred by owner on 2026-10-25**, not waived. No new code PR or repeated site probe without new evidence.

**Score/exit:** M8 **95% readiness**, still OPEN; don't claim 100% without actual post-fix UI evidence and remaining original metadata/site checks or explicit owner acceptance. Do not add more profile PRs without a real new defect. Private repository topics, decorative consistency, M4 publication and HQ branch protection / publication security PR #82 are *not* M8 gates.

## M9 — Living Governance
| Task | Color | % |
| --- | --- | ---: |
| M9 — Living Governance | 🟢 | 100% |

## M10 — GitHub Autopilot
| Task | Color | % |
| --- | --- | ---: |
| M10 — GitHub Autopilot | 🟢 | 100% |

M10 is a **historical** accepted HQ Autopilot scope; its previous scheduled worker slot was reassigned under Control Plane authority. It is not a claim of a currently running HQ executor.

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

**Next GitHub HQ priority (2026-10-26):** [#108](https://github.com/DaniilSydorenko/.github/issues/108) native `main` protection and independent security review for [#82](https://github.com/DaniilSydorenko/.github/pull/82). [AI Engineering #120](https://github.com/DaniilSydorenko/.github/issues/120) alone owns provider spending, singleton and first permitted Cursor pilot. AI PR #133–#135 now **MERGED** on the independently owned AI Engineering lane (offline tests/guards, **not** live Cursor admission). Do not duplicate their implementation, enable dispatch or build another controller. Verify one Issue→agent→CI→authorized merge→main round before unattended next-Issue execution.
