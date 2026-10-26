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
- [PR #136](https://github.com/DaniilSydorenko/.github/pull/136) accepted 2026-10-26: latest completed default-branch run **per active workflow**; reject incomplete GitHub API inventory instead of false GREEN; skip irrelevant PR-origin signals. Real HQ Help Signal post-merge smoke PASS is not proof of seven-repo rollout.
- `reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md` — synchronous HQ / scheduled Autopilot ownership boundary.

## Repository classes

A repository **may adopt** `.github/repository.json` declaring exactly one class. The owner's approved **Option B** ([Issue #56](https://github.com/DaniilSydorenko/.github/issues/56)) does **not** require local manifests across seven repositories. At the accepted discovery snapshot, Haversine had the only active local manifest; other repositories remain discoverable by registry pointers, without fabricated GRS compliance or new enforcement.

Where adopted, the class selects existing deterministic controls. Local configuration must not weaken binding safety rules for a green result. Missing optional manifests and unobserved runtime evidence are `UNKNOWN`, not automatic noncompliance.

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

The registry validator remains on-demand/non-mandatory for other repositories: owner decision [#56](https://github.com/DaniilSydorenko/.github/issues/56) **declined** new mandatory seven-repository enforcement (Option B).

## HQ ownership firewall

**No cross-repository PR WIP targets.** GitHub HQ owns shared infrastructure, not domain PR counts, backlog triage, integration, branch cleanup, product delivery or review queues. The former portfolio-wide WIP suggestion is withdrawn. Each domain may manage its own flow and dependency-bot settings independently.

HQ inspects another repository's PR metadata **only when** a specific authorized shared-infrastructure change has an actual overlapping surface, or a publication/security gate explicitly requires it. Check only relevant paths/heads/CI and preserve existing owner gates; do not turn that exception into a recurring cross-repository PR audit.

## Finish-line principle

GRS should prevent regressions and make repository expectations explicit, not create permanent governance work for its own sake.

New controls are added only when they address a demonstrated safety/correctness gap or an explicit portfolio requirement.
