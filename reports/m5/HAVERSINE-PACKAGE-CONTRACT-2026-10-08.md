# M5 — Haversine package contract and maintenance gate

Date: 2026-10-08
Status: **ACTIVE — characterization, CI, V2 core, package curation and declarations verified; dual exports still in progress**

## Purpose

Advance M5 beyond the CI/toolchain baseline by recording the current shipped package contract and separating safe maintenance work from changes that require explicit Haversine engineering decisions.

This is central read-only evidence. Haversine product/package implementation remains owned by the Haversine engineering lane.

## Verified progress since the initial package-contract baseline

The Haversine-owning lane has now materially advanced the repository beyond the initial M5 baseline.

Merged evidence includes:

- PR #39 — shipped V1 characterization coverage, exact-head CI + Gitleaks GREEN;
- PR #42 — spherical Haversine reference suite;
- PR #43 — floating-point domain guard;
- PR #45 — V2 architecture contract;
- PR #48 — V2 coordinate validation primitives;
- PR #50 — V2 distance-unit primitives;
- PR #52 — V2 pure spherical distance;
- PR #54 — generic single-pass nearest;
- PR #56 — isolated browser geolocation adapter;
- PR #58 — internal V2 core barrel;
- PR #60 — TypeScript typecheck gate;
- PR #62 — V2 core exposed through a Node-safe legacy bridge;
- PR #65 — legacy compatibility facade extracted;
- PR #67 — npm package contents curated;
- PR #69 — V1 → V2 migration guide;
- PR #71 — declaration generation + browser entry.

Current master after PR #71:
`796a159d37c8856aeb37abae7b2044d39555af5c`.

## Current package contract on master

Observed after PR #71:

- package: `haversine-geolocation@1.6.0`;
- package entry point remains `dist/build.js`;
- build now runs runtime bundle + declaration build;
- package content is curated with `files: ["dist"]`;
- TypeScript declarations are first-class at `dist/types/index.d.ts`;
- package root declares `types: dist/types/index.d.ts`;
- V2 browser entry source exists;
- CI now includes typecheck and package-content validation through the owning lane's merged work;
- no dependency or lockfile change was required for declaration generation.

The old finding “no `types` field” is therefore superseded.

## M5-C — characterization and test strategy

**Status: substantially complete for the current migration decision.**

PR #39 is merged. Its synchronized exact head passed both:

- Test and build — SUCCESS;
- Gitleaks — SUCCESS.

This establishes a behavioral safety net before V2 changes.

The existing Karma/Jasmine path remains executable and useful for browser behavior. M5 does not require replacing it merely because it is old.

A future test-runner migration remains optional and should be justified only by maintenance/reliability benefits, not fashion.

## M5-D — package contract verification

**Status: strongly advanced.**

Verified by merged owning-lane work:

- package contents are curated through `files: ["dist"]`;
- TypeScript declarations are generated;
- root declaration entry is declared;
- Node package smoke testing and npm package-content validation have been added to the owning-lane verification;
- V1/V2 compatibility structure is explicit;
- browser entry source is explicit.

Still open:

- final dual ESM/CJS runtime contract;
- conditional `exports` map;
- final root/browser/legacy subpath contract;
- exact supported Node/browser matrix;
- final packed-tarball proof after exports are complete.

## Active package-contract experiment

Draft PR #73 — `build: add dual ESM/CJS package exports` — is the current Haversine-owning lane frontier.

Its scope proposes:

- root ESM/CJS artifacts;
- browser ESM/CJS artifacts;
- legacy ESM/CJS artifacts;
- conditional exports for root, browser, legacy and package.json;
- `main`, `module`, `types`, and `sideEffects`;
- real packed-tarball installs into temporary CommonJS and ESM consumers.

Current exact head `7192d764cee609b0d79eef580277605f25faeb9d` has Secret Scan SUCCESS.

Because PR #73 remains draft, central governance must not treat the proposed exports contract as accepted or merged.

## M5-E — dependency maintenance

The old Dependabot PRs #24–#31 remain open and stale.

They must not be merged merely to reduce open PR count.

The correct order remains:

1. current dependency graph;
2. current audit evidence;
3. classify each old PR as obsolete, superseded, current, or intentionally deferred;
4. remediate through fresh focused PRs only when still relevant;
5. exact-head install/test/build proof.

## M5-F — release readiness

A new npm release should occur only when there is a coherent user-facing package contract to release.

The strongest likely release boundary is after:

- the V2 compatibility architecture is stable;
- the exports contract is accepted;
- package tarball consumers pass in both module systems;
- migration documentation is aligned with shipped behavior;
- dependency/security review is current;
- version semantics and release notes are explicit;
- publishing uses a safe short-lived/provenance-capable model.

No release should be created solely to make the repository appear active.

## Current M5 assessment

M5 is no longer primarily a modernization-planning milestone.

It has become an implementation-and-release-readiness milestone with substantial engineering proof already merged.

Current state:

- M5-A executable CI — **DONE**;
- M5-B toolchain inventory — **DONE**;
- M5-C characterization — **DONE for current V2 migration**;
- M5-D package contract — **ADVANCED; dual exports pending**;
- M5-E dependency/security remediation — **PENDING CURRENT GRAPH/AUDIT**;
- M5-F release readiness — **PARTIAL**;
- M5-G flagship polish — **PARTIAL**.

Central governance should now follow the Haversine-owning lane's real engineering evidence rather than duplicate it.
