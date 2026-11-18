# AI Engineering Governance — adoption inventory

Last verified: 2026-11-18, GitHub installation repository listing (17 repositories; pagination exhausted). **Inventory ≠ adoption.** All existing domain repositories remain unmodified.

## Active repositories

| Repository | Default branch | Local AGENTS.md | Governance adoption | Domain caveat |
| --- | --- | --- | --- | --- |
| DaniilSydorenko/.github | main | Present | PROPOSED in Draft PR #166; CI must match exact HEAD | HQ owns shared infrastructure, not domain PRs |
| DaniilSydorenko/haversine-geolocation | master | Present | CANDIDATE; no adoption PR | Preserve v2 roadmap and local master baseline |
| DaniilSydorenko/listing-kit | main | Present | CANDIDATE; no adoption PR | Private alpha, privacy and white-hat rules |
| DaniilSydorenko/engineering-labs | main | Present | CANDIDATE; no adoption PR | Public-safe learning; no employer branding |
| DaniilSydorenko/career-intelligence | main | Present | CANDIDATE; no adoption PR | Lovable sync/history restrictions |
| DaniilSydorenko/engineering-handbook | main | Present | CANDIDATE; no adoption PR | Theory ownership and publication gates |
| DaniilSydorenko/autopilot-control-plane | main | Present | CANDIDATE; no adoption PR | Observer, not worker dispatcher |
| DaniilSydorenko/DaniilSydorenko | main | Not found at root | CANDIDATE; no adoption PR | Profile repository; may not need agent governance |

## Archived repositories — inventory only

| Repository | Default branch | Adoption |
| --- | --- | --- |
| DaniilSydorenko/old_debris | master | EXCLUDED pending owner decision (archived) |
| DaniilSydorenko/flex-mix | master | EXCLUDED pending owner decision (archived) |
| DaniilSydorenko/chocolate.grid.js | master | EXCLUDED pending owner decision (archived) |
| DaniilSydorenko/frontend-software-engineer-portfolio | master | EXCLUDED pending owner decision (archived) |
| DaniilSydorenko/performy | master | EXCLUDED pending owner decision (archived) |
| DaniilSydorenko/football-matches-predictor | master | EXCLUDED pending owner decision (archived) |
| DaniilSydorenko/masurian-lakes | master | EXCLUDED pending owner decision (archived) |
| DaniilSydorenko/graphql-simple-app | master | EXCLUDED pending owner decision (archived) |
| DaniilSydorenko/listing-assistant | main | EXCLUDED pending owner decision (archived) |

## Rollout sequencing and authority

1. Finish/verify central PR #166 and obtain owner merge approval. The main-branch policy URL in the adoption kit does **not** yet point to accepted governance.
2. Prepare a bounded per-repository read-only compatibility assessment of local AGENTS.md and required CI. Preserve stronger domain restrictions.
3. Propose repository-owned adoption PRs **one at a time** after verifying no competing writer and owner authorization; no mass commit, no auto-merge.
4. Separately audit effective CI branch protection and worker bootstrap. Documentation-only adoption never earns `ENFORCED`.
5. For future repos, require explicit use of a reviewed bootstrap template; template not yet created or installed.

## Current metrics

- Installed repositories inventoried: **17** (8 active, 9 archived).
- Active repositories with root AGENTS.md found: **7 of 8**.
- Domain repositories modified by this rollout: **0**.
- Governance adoption PRs outside central HQ: **0**.
- Repositories with verified runtime enforcement of this new policy: **0**.
- Unknown: additional repositories outside the GitHub installation visibility, effective per-repo rulesets, non-GitHub agent launch paths.

**No cross-repository adoption is asserted.** No broad repository writes, merge, ruleset, secret or billing changes were made.
