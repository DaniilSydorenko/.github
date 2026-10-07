# GRS rollout readiness — Haversine

Date: 2026-10-07
Status: **READY — public OSS governance baseline established**

## Classification

- GRS class: `oss-library`
- maturity: `active`
- visibility: `public`
- portfolio intent: flagship / pin candidate
- central manifest: `grs/pilots/haversine-geolocation.repository.json`
- default branch: `master`

## Verified outcome

Haversine completed the M3 GitHub-governance remediation lane without changing library behavior.

Merged consumer PR #33 established:

- `.github/repository.json`
- `.github/workflows/grs.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `SECURITY.md`
- `CONTRIBUTING.md`
- bug and feature issue templates

The remediated exact head `d1d279615298b8a9e2b330f3c6e68ec01e1ac20f` passed:

- GRS Governance — SUCCESS
- Secret Scan — SUCCESS

PR #33 merged as `3d52064f66b8c10d12a291bbfd4836486d34f3e7`.

A separate documentation-only PR #34 then refreshed the OSS README and merged as `cca67721d5be5bb3c3d1f8d34efcb34e6792d578`.

## Boundaries preserved

This M3 lane did not:

- change library behavior or public API;
- modernize dependencies;
- publish a new npm release;
- change the default branch;
- weaken GRS controls.

Further Haversine engineering belongs to the Haversine/OSS roadmap rather than M3 readiness.
