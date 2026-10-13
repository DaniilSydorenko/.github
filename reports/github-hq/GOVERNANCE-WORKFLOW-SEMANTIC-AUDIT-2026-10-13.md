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
