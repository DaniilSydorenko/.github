# GRS pilot readiness assessment — 2026-10-06

This is a central, read-only pre-rollout assessment. It does not modify consumer repositories.

## DaniilSydorenko/DaniilSydorenko

Target class: `profile`
Visibility: public
Default branch: `main`

Verified:
- profile README exists and provides current engineering positioning;
- repository is active/public;
- current GRS pilot manifest can represent it without overrides;
- profile class intentionally does not require product-style tests, issue taxonomy, licensing, SECURITY.md, or CONTRIBUTING.md.

Open before final M2 closeout:
- repository metadata remains an M2 presentation task where GitHub mutation tooling permits;
- public-fact QA remains required for claims such as experience duration and external website linkage;
- pin application remains an owner/UI operation.

Pilot decision: **READY after GRS bootstrap merge**.

## DaniilSydorenko/haversine-geolocation

Target class: `oss-library`
Visibility: public
Default branch: `master`

Verified:
- README and MIT license text are present;
- package metadata identifies MIT licensing and npm package `haversine-geolocation`;
- build and Karma test scripts exist;
- a full-history secret-scan workflow exists with immutable checkout SHA;
- current README still exposes a legacy Travis CI badge;
- `SECURITY.md` was not found in default-branch code search;
- `CONTRIBUTING.md` was not found in default-branch code search.

GRS implication:
- Haversine is a strong pilot because it exercises real `oss-library` requirements instead of merely passing the minimal profile class.
- Do not disguise missing OSS governance surfaces. Initial consumer rollout should be allowed to report truthful FAIL/WARN findings before remediation.
- GitHub-facing governance/remediation must not redefine Haversine engineering architecture; substantive modernization remains owned by the GEO/HAVERSINE workstream.

Pilot decision: **READY FOR AUDIT after profile consumer pilot; remediation follows measured findings**.

## Rollout order

`GRS bootstrap merge → profile consumer PASS → Haversine consumer audit → targeted Haversine governance remediation → broader active-repository rollout`
