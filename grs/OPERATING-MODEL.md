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

## Finish-line principle

GRS should prevent regressions and make repository expectations explicit, not create permanent governance work for its own sake.

New controls are added only when they address a demonstrated safety/correctness gap or an explicit portfolio requirement.
