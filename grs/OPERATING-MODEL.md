# GRS Operating Model

Status: ACTIVE

GRS is the central GitHub governance layer for the portfolio. It is deliberately smaller than a full compliance framework: deterministic controls are enforced only where the signal is reliable enough to fail closed.

## Sources of truth

- `grs/repository.schema.json` — manifest contract.
- `grs/validator.py` — structural manifest validation.
- `grs/classes/profiles.json` — executable repository-class file-surface policy.
- `grs/audit_repository.py` — repository-surface enforcement.
- `grs/check_policy_drift.py` — taxonomy drift detection across schema, validator, class profiles and pilot manifests.
- `grs/publication/*.publication.json` — public/private extraction boundaries.
- `grs/publication/validate_publication.py` — publication-boundary validation.
- `grs/publication/audit_history_paths.py` — read-only history path audit.
- `.github/workflows/grs-control-plane.yml` — regression and policy validation.
- `.github/workflows/reusable-autopilot-health.yml` — fail-closed Actions health signal.
- `reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md` — synchronous HQ / scheduled Autopilot ownership boundary.

## Repository classes

Each governed repository declares exactly one class in `.github/repository.json`.

The class selects default deterministic controls. Repository-local configuration must not silently weaken non-overridable safety controls merely to obtain a green result.

Machine-readable class profiles are intentionally limited to low-false-positive checks such as README/status, licensing where deterministic, collaboration surfaces and secret-hygiene workflow presence.

## Drift protection

The GRS Control Plane fails when the class taxonomy diverges between:

1. the JSON schema;
2. validator allow-lists;
3. executable class profiles;
4. pilot manifests that reference unknown classes.

Class-policy changes therefore require synchronized policy, executable data and tests in the same pull request.

## Publication safety

GRS publication policy is separate from repository visibility.

A repository can be governance-green while still being unsafe or immature for public release.

Private → public remains an explicit owner decision after:

- sensitive-surface extraction;
- history review where needed;
- exact-head CI/security/governance checks;
- product/readiness gates owned by the relevant domain.

## Autopilot relationship

Autopilot may detect drift, prepare bounded maintenance and report repository health.

Autopilot does not own:

- repository visibility;
- destructive history rewrites;
- credential changes;
- evidence inflation;
- product/domain implementation outside its boundary;
- the synchronous HQ roadmap.

Before mutation, workers inspect live repository state and avoid overlapping branches/surfaces.

## Engineering discovery

The governed engineering repositories are discoverable through:

- `governance/ENGINEERING-STATE.md` — human-readable entrypoint;
- `governance/repository-registry.json` — machine-readable pointer registry;
- `grs/validate_repository_registry.py` — local/read-only structural validator.

The registry standardizes discovery, not repository file layouts. It points to local canonical roadmaps, authority documents, agent guidance and specialized trackers without copying mutable progress, PR, CI or runtime state.

The registry validator is intentionally not a required cross-repository CI gate until the remaining Governance v1 enforcement/adoption decision is approved.

## Pull-request WIP limits — owner-requested, advisory (seven-repository scope)

The recommended **flow target** per repository is **at most 3 open human-authored PRs**, with **at most 1 active Draft** and normally **at most 2 review-ready PRs**. These are independent delivery units, not a limit on accepted commits or releases. Prefer finish/merge/rework before starting another nonurgent PR. Domain owners decide their own queues and merges; GitHub HQ does not close their PRs.

Dependency bot updates target **at most 3 routine open PRs per repository**; group compatible updates using existing bot configuration when useful. Never defer a critical security fix solely to satisfy a number. Any change to bot settings is repository-owned, not a cross-repository HQ mutation.

Intentional stacked work should preferably stay within **5 dependent PRs** and expose its dependency order. Existing deeper stacks (notably Handbook) are **grandfathered**: inspect parent/child branches, preserve all unique work, and reduce incrementally through authorized domain integration. Never bulk-close, force-push, delete branches, bypass reviews, or falsely mark work completed to meet a target.

When above target: finish one eligible PR first, or record one precise BLOCKED/owner-gated exception and continue independent low-collision work. A blocked security/publishing review may stay open without freezing unrelated work. Count Draft, ready, stacked and bot PRs separately; do not treat the aggregate count as an enforcement gate or a product-completion score.

**Scope:** an operating guideline requested by the owner, **not** a new mandatory C01–C07 fleet policy. No new workflow, recurring auditor, PR status database, issue-per-PR ceremony or required CI check. Domain owners retain final authority and may document necessary exceptions in an existing PR or Issue.

## Finish-line principle

GRS should prevent regressions and make repository expectations explicit, not create permanent governance work for its own sake.

New controls are added only when they address a demonstrated safety/correctness gap or an explicit portfolio requirement.
