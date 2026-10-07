# M5 — Haversine OSS Flagship baseline

Date: 2026-10-07
Status: **ACTIVE — governance ready, engineering modernization pending**

## Purpose

Establish the first evidence-based M5 baseline for `DaniilSydorenko/haversine-geolocation` after M3 governance adoption.

M5 is not a rewrite mandate. It upgrades a real, long-lived OSS package into a stronger maintained flagship through small, verifiable engineering units.

## Current verified strengths

- public repository with long-lived history;
- npm package identity and homepage already configured;
- MIT license;
- 27 GitHub stars and 2 forks at this snapshot;
- GRS consumer installed and green;
- SECURITY.md, CONTRIBUTING.md, PR template and issue taxonomy present;
- full-history secret scan present and green on the M3 remediation head;
- README refreshed in a separate documentation PR;
- release history exists through v1.6.0.

## Current engineering baseline

The package remains on a legacy build/test stack:

- package version: `1.6.0`;
- TypeScript: `^4.4.4`;
- Webpack 5-era build;
- Karma + Jasmine browser tests;
- Babel 7-era transform stack;
- latest GitHub release: v1.6.0, published in 2021.

There is currently no dedicated general-purpose CI workflow on the default branch that proves `npm test` and `npm run build` on ordinary pull requests. The active GitHub workflows are governance, secret scanning, and autopilot assistance.

This means M5 should prioritize executable engineering proof before cosmetic modernization.

## Open maintenance debt

Several old Dependabot pull requests remain open from the earlier maintenance period. They should not be merged mechanically.

Each dependency update must be classified as one of:

- still relevant and safe after fresh compatibility/testing evidence;
- superseded by a broader modernization unit;
- obsolete because the dependency is removed/replaced;
- intentionally deferred.

Closing or merging stale dependency PRs is a deliberate maintenance action, not a cleanup checkbox.

## M5 recommended sequence

### M5-A — Executable CI baseline

Goal: make every future change provable.

Required:

1. run supported Node versions in GitHub Actions;
2. `npm ci`;
3. `npm test`;
4. `npm run build`;
5. keep secret scan + GRS independent;
6. pin third-party Actions by immutable SHA;
7. do not change package behavior in this unit.

Acceptance: real executed CI steps are GREEN on exact PR head.

### M5-B — Dependency/toolchain inventory

Produce a fresh dependency map:

- runtime vs dev dependencies;
- direct vs transitive security alerts;
- deprecated packages/plugins;
- Node/browser compatibility constraints;
- TypeScript/Babel/Webpack/Karma modernization options.

Do not batch-upgrade blindly.

### M5-C — Test modernization decision

Decide whether Karma/Jasmine remains justified.

Possible outcomes:

- retain and harden;
- migrate to a simpler modern runner;
- split pure-function tests from browser-specific tests.

The decision must be driven by actual package behavior and compatibility, not trend-following.

### M5-D — Build/package contract

Verify:

- package entry point;
- generated files included in `npm pack`;
- TypeScript declarations, if promised;
- ESM/CommonJS expectations;
- Node/browser support;
- package size;
- clean install/build/test from a fresh checkout.

### M5-E — Dependency remediation

Only after CI exists:

- update dependencies in small coherent batches;
- use current tests/build as gates;
- close or supersede stale Dependabot PRs with explicit rationale;
- never treat a bot compatibility score as sufficient proof.

### M5-F — Release pipeline

Before a new release:

- explicit versioning decision;
- changelog/release notes;
- npm publishing security model;
- prefer trusted/OIDC publishing + provenance where supported over long-lived publish tokens;
- verify package tarball before publish;
- no release purely to create activity.

### M5-G — Flagship polish

After engineering gates are real:

- final README/API examples;
- metadata/topics;
- support/maintenance status;
- badges only for checks that actually run;
- architecture/trade-off notes where they add value;
- pin/profile integration.

## Boundaries

M5 must not:

- fabricate active maintenance history;
- rewrite package behavior without evidence;
- merge old dependency PRs without fresh tests;
- publish a release without an intentional release reason;
- break users merely to modernize syntax/tooling;
- weaken GRS/security checks.

Substantive API changes remain a dedicated Haversine engineering decision.

## Current conclusion

Haversine has completed governance readiness, but the next highest-value improvement is **real build/test CI on the current package before dependency modernization**.

That CI baseline is the first recommended implementation unit for the Haversine-owning engineering lane.
