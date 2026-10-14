# Semantic workflow audit — first verified batch (2026-10-13)

Status: read-only findings; no CI/security policy changed. Scope: central GRS Control Plane; ListingKit CI/Secret Scan; Haversine CI/GRS/Secret Scan. This is **not** a fleet-wide YAML audit.

## Verified findings

| ID | Evidence | Classification | Next action |
| --- | --- | --- | --- |
| WF-01 | Central `.github/workflows/grs-control-plane.yml` checks out immutable SHA, sets `persist-credentials: false`, and has `contents: read`. Its PR trigger paths cover `governance/**`, `grs/**`, workflow templates and select workflows; **not `reports/**`**. | Correct scoped control; documentation-only PR #79 does not trigger it | Do not claim PR #79 has CI. Consider a separate lightweight docs check only if recurring value justifies cost |
| WF-02 | Haversine `.github/workflows/grs.yml` checks out the central `.github` repository using `ref: main`, without `persist-credentials: false` on either checkout. | **[NEW] Supply-chain reproducibility/credential-minimization gap** compared with central policy, not proof of compromise | Evaluate immutable central revision pin or versioned release reference with explicit upgrade process; set checkout credential minimization; test in domain-owned PR, do not edit Haversine from HQ |
| WF-03 | ListingKit `ci.yml` checkout for quality uses `persist-credentials: false`, full history; build checkout has full history but no explicit `persist-credentials: false`. | **[NEW] Inconsistent credential minimization** inside same CI | Confirm job requirements and propose safe local adjustment via Ladvero owner |
| WF-04 | ListingKit `secret-scan.yml` and Haversine `secret-scan.yml` use same SHA-pinned Gitleaks Action and `fetch-depth: 0`; both schedule weekly and expose manual dispatch. | Legitimate shared baseline, not proof of complete historical coverage on PR events | Keep full-history execution/verification distinct from incremental PR scan; preserve scanner protections |
| WF-05 | Haversine `ci.yml` includes library-specific packed CJS/ESM, Node and npm package validations. ListingKit `ci.yml` includes product-specific Yarn/Turbo/Nuxt build and design gates. | **Legitimate domain specialization**, not duplication to remove | Preserve local CI; centralize only common contracts |
| WF-06 | Central GRS validates pilot manifests; only Haversine currently has `.github/repository.json` among seven governed repositories. | Adoption gap, not evidence that other repos have no security controls | Owner gate #56 before mandatory rollout |

## Safety and scope

- No deletion, no workflow edits, no local repo mutation.
- `ref: main` in Haversine is an observed moving dependency; this alone does not establish malicious behavior or a failed workflow.
- Gitleaks `fetch-depth: 0` does not prove full-history scanning for every event; review action invocation and logs for actual coverage.
- Exact-head CI on PR #79 is **not observed**; central GRS workflow path filter excludes this report-only PR.
- Next batch: Control Plane, Career Intelligence, Handbook, Labs and profile workflows; then branch/ruleset inventory. Cross-repository fixes remain domain-owned.

## Second verified batch: five-domain workflow metadata (2026-10-13)

Inspected full workflow text in `autopilot-control-plane` (6 files), `career-intelligence` (4), `engineering-handbook` (3) and `engineering-labs` (3); profile workflow inspection is still pending.

- **WF-07 — shared health mutable reference:** all four repos call `DaniilSydorenko/.github/.github/workflows/reusable-autopilot-health.yml@main`. This is a deliberate shared implementation, but a moving ref; evaluate version pinning and upgrade cadence, balancing rapid central security patches against reproducibility.
- **WF-08 — Control Plane write-job checkout:** `issue-sync.yml`, `reconcile.yml`, `roadmap-executor.yml`, and `weekly-review.yml` each have a checkout without explicit `persist-credentials: false`; `validate.yml` sets it false. The write jobs may legitimately need authenticated pushes. Inspect the actual git-push/auth model before proposing changes; **do not blindly disable credentials or break the worker**.
- **WF-09 — consistent read-only workflows:** Career Intelligence public-runtime-smoke, validate and secret-scan, Handbook validate and secret-scan, and Labs quality and secret-scan explicitly set `persist-credentials: false` and `contents: read`. This is positive evidence of existing local hardening.
- **WF-10 — security scan scope:** Career Intelligence, Handbook and Labs each expose a local `secret-scan.yml`; central `.github` and Control Plane do not expose that exact filename. Equivalent checks and historical execution remain unverified; classify as coverage questions, not confirmed absence.
- **WF-11 — scope of this batch:** 16 workflow files inspected for selected structural and permission patterns, not a full threat-model or every line of job scripts. Do not interpret pattern counts as a vulnerability assessment.

**Updated remediation sequence:** prioritize central shared-workflow versioning decision, GRS `ref: main` reproducibility, non-writing checkout credential minimization, then inspect write-job authentication dependencies; all actual domain workflow changes require domain-owner coordination and exact-head CI.
