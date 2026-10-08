# M5 — Haversine package contract and maintenance gate

Date: 2026-10-08
Status: **ACTIVE — package/release contract measured; modernization decisions pending**

## Purpose

Advance M5 beyond the CI/toolchain baseline by recording the current shipped package contract and separating safe maintenance work from changes that require explicit Haversine engineering decisions.

This is read-only evidence. It does not modify the package, dependencies, release, API, or visibility.

## Verified current package contract

Observed on `master` after M5-A:

- package: `haversine-geolocation@1.6.0`;
- package entry point: `dist/build.js`;
- build: Webpack production bundle;
- bundle format: UMD;
- source language: TypeScript;
- TypeScript compiler target: ES6;
- TypeScript module target: CommonJS;
- Babel target configuration includes browser defaults and IE >= 11;
- no `types` field declared;
- no `exports` field declared;
- no `engines` field declared;
- no runtime dependencies declared in `package.json`;
- build/test tooling is devDependency-only;
- `.npmignore` is minimal and does not itself prove a narrow published tarball.

These observations describe configuration. They are **not** proof that every implied browser/Node environment is supported.

## Current CI proof

M5-A established executable CI with:

- Node.js 22;
- `npm ci`;
- Karma/Jasmine test execution through Xvfb;
- `npm run build`;
- immutable-SHA-pinned GitHub Actions.

This provides a real modernization gate, but it proves one current environment rather than a full support matrix.

## M5-C — test strategy decision

The existing Karma/Jasmine suite is now executable in CI. Therefore there is no justification for replacing it merely because it is old.

Recommended sequence:

1. land characterization coverage through the Haversine-owning lane after exact-head CI proof;
2. identify which tests actually need a browser;
3. separate pure distance/selection behavior from browser Geolocation behavior;
4. only then decide whether to retain Karma/Jasmine, migrate pure tests, or split the suite.

Acceptance for a migration decision:

- current V1 behavior is captured;
- old and new test paths agree on supported behavior;
- no product behavior changes are hidden inside tooling migration;
- exact-head CI remains green.

## M5-D — package contract verification

Before changing packaging fields, the owning lane should produce evidence for:

1. `npm pack --dry-run --json`;
2. fresh install of the generated tarball;
3. CommonJS/Node consumption of the declared `main` entry;
4. browser/UMD consumption;
5. whether TypeScript declarations are intentionally supported;
6. package contents and size;
7. supported Node/browser matrix;
8. whether `src`, tests, docs, maps, or other files are unintentionally shipped.

Only after this evidence should `files`, `exports`, `types`, `engines`, ESM/CJS dual packaging, or declaration generation be proposed.

## M5-E — stale dependency maintenance classification

The repository currently has old Dependabot PRs #24–#31 from 2022–2023.

Current classification:

| PR | Dependency area | M5 handling |
| --- | --- | --- |
| #24 | terser | stale; re-evaluate through current dependency tree |
| #25 | socket.io-parser | stale/transitive; do not merge independently without current graph |
| #26 | loader-utils | stale/transitive; do not merge independently without current graph |
| #27 | engine.io / socket.io | stale/transitive; do not merge independently without current graph |
| #28 | qs / body-parser | stale/transitive; do not merge independently without current graph |
| #29 | json5 | stale/transitive; do not merge independently without current graph |
| #30 | ua-parser-js | stale/transitive; do not merge independently without current graph |
| #31 | minimist | stale/transitive; do not merge independently without current graph |

These PRs are historical security/maintenance signals, not current merge candidates.

Recommended owning-lane action after a fresh `npm ls --all` + `npm audit --json`:

- close as superseded when the dependency is no longer present or the required version is already reached by a broader update;
- replace with a current focused remediation PR when still relevant;
- keep only when exact-head install/test/build proves the old PR remains a clean, minimal fix.

No stale Dependabot PR should be merged merely to reduce the open-PR count.

## Characterization PR #39

PR #39 is a valuable M5 input because it documents shipped V1 behavior without production changes.

However its current head predates the merged CI baseline. M5 should not infer GREEN status from the default branch.

Required before merge:

- synchronize/recreate through the Haversine-owning lane;
- require exact-head CI + secret/governance checks;
- confirm it remains test-only;
- then merge under the owning lane's authority.

## M5-F — release readiness

A new npm release is **not yet justified solely by repository modernization**.

Before any release:

- define the user-facing reason for the release;
- verify package tarball contract;
- decide version semantics;
- prepare changelog/release notes;
- verify publish authentication and provenance model;
- prefer short-lived trusted/OIDC publishing where supported;
- verify the exact package artifact before publish.

No release should be created merely to make the repository look active.

## Current decision

M5-A is complete and M5-B inventory is complete.

The next substantive Haversine-owning work should be:

```text
characterization evidence
→ package contract verification
→ current dependency/security inventory
→ bounded toolchain/dependency decisions
→ release readiness
```

Central GitHub governance should continue to record evidence and enforce truthful gates without taking ownership of Haversine product behavior.


## M5-D/E — exact-blob evidence addendum (2026-10-08)

On Haversine `master@4316daf0d5b6b1fbe2b208e54ac6d80cfe9824f6`, live Git tree confirms `package.json` blob `5ef275a3e6a19b3bc64cbd2aa0408f8285dfc91f` (1,573 bytes), `dist/build.js` blob `a262f6f96fa534587339cf670970b877d1f2cfec` (5,237 bytes), and `package-lock.json` blob `e8464ab8cb1405690e3ebbcf3a9784dd85834d74` (349,986 bytes).

**M5-D:** Earlier read-only local Node.js 22.16.0 reproduction using exact package and bundle blobs failed on plain package-root `require()` with `ReferenceError: window is not defined`. A diagnostic-only `global.window={}` shim allowed import and a 111.2 km distance calculation. This confirms a repository-entry Node initialization failure, not npm tarball identity or a supported shim. Historical issue #12 reports the same error. Still missing: actual `npm pack` inventory, tarball install, browser UMD test, declaration intent and support matrix.

**M5-E:** Prior static inspection of lockfile v2 found 422 package entries and historical Dependabot-target package names still locked: terser 5.9.0, socket.io-parser 4.0.4, loader-utils 1.4.0, engine.io 6.0.1, socket.io 4.3.2, qs 6.7.0, body-parser 1.19.0, json5 2.2.0/1.0.1, ua-parser-js 0.7.31 and minimist 1.2.5. These are transitive dev entries, not verified vulnerabilities. Owning lane must provide exact-head `npm ls --all`, `npm audit --json`, install/test/build evidence before old PR dispositions. No consumer edits or release authority are implied.
