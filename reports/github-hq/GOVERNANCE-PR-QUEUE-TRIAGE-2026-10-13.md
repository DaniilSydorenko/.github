# Seven-repository PR queue triage — 2026-10-13

**Scope:** read-only live GitHub REST `pulls?state=open&per_page=100` per seven approved repositories. This is a point-in-time snapshot, not a new tracker. No PRs closed or merged by this audit. No branches deleted.

| Repo | Open | Draft | Initial disposition |
| --- | ---: | ---: | --- |
| .github | 1 | 1 | #79 documentation/governance consolidation; review, check latest HEAD and approval #56 boundary |
| autopilot-control-plane | 0 | 0 | No PR cleanup needed |
| listing-kit | 6 | 1 | #194 security Draft remains blocked pending full-history Gitleaks rerun/owner classification; #193 keyboard smoke, #180 product UI, #169/#190/#191 Dependabot remain domain-owned |
| career-intelligence | 7 | 0 | #94 and #50 PUBLIC docs may overlap; #69–#73 dependency PRs; inspect file overlap and CI before merges |
| engineering-handbook | 44 | 43 | **Primary queue risk**; stacked/overlapping draft content; #84 explicitly forward-ports #82/#81 and #83; #84 reports broken flattened Markdown relative links, 0% release readiness. No blanket close |
| engineering-labs | 0 | 0 | No PR cleanup needed |
| haversine-geolocation | 1 | 0 | #152 TypeScript major-version Dependabot; domain-owner review and consumer fixtures required |
| **Total** | **59** | **45** | 44 Handbook PRs = 74.6% of fleet queue; 43 of 45 drafts there |

## Collision and cleanup decision

- **KEEP/BLOCK:** ListingKit #194 until the **historical** Gitleaks verification is demonstrated. PR green incremental scan is not full-history clearance.
- **KEEP/INVESTIGATE:** Handbook #84, #83, #82, #81 and upstream drafts. #84's own PR description says it stacks #82 (which contains #81), forward-ports #83, and has unresolved generated-book relative-link breakage. Before closing any predecessors, compare unique commits/changed files, check references/required CI and obtain Handbook owner disposition.
- **INVESTIGATE:** Career #50 vs #94, likely roadmap/document overlap, not proven redundant until diff and current-main comparison.
- **INVESTIGATE:** All Dependabot PRs need CI, dependency compatibility, owner approval and exact-head checks; never auto-merge major TypeScript upgrade #152.
- **KEEP:** HQ #79 is a Draft evidence PR; no applicable workflow runs were observed on its report-only HEAD because central GRS path filters exclude `reports/**`. Mergeability is not a security/acceptance verdict.

## Bounded next actions

1. Domain-owned Handbook **stack graph + changed-file collision map** for #14, #22–84; designate one integration sequence and explicit owner approval; close superseded drafts only after verifying no unique work or open dependent branch. Never mass-close by age.
2. Domain-owned Ladvero #194 historical Gitleaks rerun and classification; preserve blocked status.
3. HQ #79 evidence review and acceptance, then small read-only GRS conformance reporter PR. Do not bypass issue #56.
4. Career #50/#94 diff and baseline comparison; separate product/public progress from HQ governance.
5. Haversine #152 test TypeScript 7 consumer and declaration compatibility before any merge.

## Scope and metrics

- The owner-approved seven-repository scope freeze defers M6 Norway Geo and M7 External OSS. The original HQ 88% and Governance v1 90% are retained as historical baseline, not raised by PR cleanup or scope reduction.
- 59 open PRs are **not** 59 defects; queue size alone is not an implementation completion metric.
- Final GOV-M07/M08 acceptance requires validated seven-repo GRS dimensions, worker policy consumption proof, one full Haversine engineering cycle, explicit owner gate #56 and reproducible evidence.
