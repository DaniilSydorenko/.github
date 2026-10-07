# GRS rollout readiness — Haversine

Date: 2026-10-07
Status: **ACTIVE REMEDIATION — public OSS repository**

## Scope

This readiness record captures live GitHub-governance evidence for `DaniilSydorenko/haversine-geolocation` without changing product behavior.

## Classification

- GRS class: `oss-library`
- maturity: `active`
- visibility: `public`
- portfolio intent: flagship / pin candidate
- central manifest: `grs/pilots/haversine-geolocation.repository.json`
- default branch: `master`

## Live measured baseline

| Surface | Observed on `master` before remediation | GRS v1 interpretation |
| --- | --- | --- |
| README.md | present | PASS |
| repository metadata | description, topics and npm homepage present | PASS / existing surface |
| .gitignore | present | PASS |
| MIT license | present | PASS |
| secret-scan workflow | present | PASS |
| PR template | not on base; present in PR #33 | remediation in progress |
| repository manifest | not on base; present in PR #33 | remediation in progress |
| GRS consumer workflow | not on base; present in PR #33 | remediation in progress |
| SECURITY.md | not on base; added to PR #33 | remediation in progress |
| CONTRIBUTING.md | not on base; added to PR #33 | remediation in progress |
| issue taxonomy | not on base; bug/feature templates added to PR #33 | remediation in progress |
| release history | releases exist through v1.6.0 | present, modernization still separate |

## Remediation unit

Consumer PR #33, `feat(grs): adopt OSS repository governance`, is the active governance-only unit.

Initial exact-head GRS execution ran real steps and failed truthfully at the deterministic repository-surface audit. The failure was not infrastructure/prestart: checkout and manifest validation succeeded, then the surface audit failed on missing required OSS governance files.

The PR now includes the measured required surfaces rather than weakening GRS:

- `.github/repository.json`
- `.github/workflows/grs.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`

The current head after remediation is expected to be validated by the existing GRS workflow before any merge decision.

## Non-goals

This unit does not:

- change library behavior;
- modernize dependencies;
- rewrite the README;
- change the default branch;
- publish a new npm release;
- alter package API or runtime support;
- weaken GRS controls.

Substantive Haversine engineering remains with the GEO/HAVERSINE owner.

## Next gate

Require the remediated PR #33 exact head to execute real GRS steps and reach GREEN. After that, merge authority must follow the current owner/autopilot policy, and any further OSS modernization should be a separate, evidence-driven unit.
