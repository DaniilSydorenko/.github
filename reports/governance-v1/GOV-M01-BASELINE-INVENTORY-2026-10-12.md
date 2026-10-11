# Engineering Governance v1 — GOV-M01 Baseline Inventory

Date: 2026-10-12
Status: COMPLETE for the observed checkpoint
Scope: seven repositories only

Default branches are canonical unless an accepted repository policy says otherwise. Open feature branches and pull requests are evidence, not accepted state.

## Repository baseline

| Repository | Visibility | Canonical branch | Observed SHA | Active PRs | Key artifacts | Recent evidence |
|---|---|---|---|---|---|---|
| `DaniilSydorenko/.github` | public | `main` | `421710b650ded94aca81a1cd13354f5f46675cff` | none | HQ roadmap, GRS docs, HQ/Autopilot boundaries | GRS Control Plane success on observed main |
| `DaniilSydorenko/autopilot-control-plane` | private | `main` | `44fded3e5cefe54ccdec3bbeb15d6d0b51097a15` | none | `CONTROL_PLANE.md`, `ROADMAP.md`, `FLEET.yaml`, `AUTHORITY.md` | Validate/Reconcile recently successful; Issue #139 open |
| `DaniilSydorenko/listing-kit` | private | `main` | `46210e0a686c86a290071b8ae1e9d0ee86d2c0a2` | #189, #180, #169 | `AGENTS.md`, `ROADMAP.md`, `TASKS.md`, `docs/mvp/MVP_READINESS.md` | PR #189 CI + Secret Scan success |
| `DaniilSydorenko/career-intelligence` | private | `main` | `164cf6e7539043d4fa2b67209311c817272c5e0a` | #67, #63, #50 | root `AGENTS.md` currently Lovable-history-only | Validate + Secret Scan success on observed main |
| `DaniilSydorenko/engineering-handbook` | private | `main` | `5f422b0b198dd8c5bdf445b1f11f74034ac5ddff` | stacked draft chain plus #14 | no root `AGENTS.md` observed | Handbook Validate + Secret Scan success |
| `DaniilSydorenko/engineering-labs` | private | `main` | `25ca1a82d0e1973993fdd882116bcf3ef6d34c6e` | none | `AGENTS.md`, mission docs, public-safety docs | Quality + Secret Scan success |
| `DaniilSydorenko/haversine-geolocation` | public | `master` | `3f184283b31ccdf8dd177126bd911ce4bd71f967` | #150 | `docs/roadmap/haversine-v2-human-roadmap.md` | PR #150 CI, compatibility, benchmarks, consumer fixtures and Secret Scan success |

## Active issue / defect evidence

- Control Plane Issue #139 — scheduled scheduler-snapshot autonomy proof did not persist.
- Haversine Issues #149 and #74 remain open.
- ListingKit Issues #16–#23 are product-owned and are not governance-owned work.
- Career Intelligence, Handbook and Labs had no open standalone Issues at this checkpoint.

## Branch / PR interpretation

Open PRs may contain newer implementation or roadmap state than the default branch, but they are not accepted canonical state until merged according to repository policy.

- Haversine `master` reports 94% on the V2 human roadmap while PR #150 contains newer lint/format work.
- ListingKit has three live PRs; `main` remains product truth until accepted merge.
- Career Intelligence has three live PRs with newer ingestion/public-test/public-roadmap work.
- Engineering Handbook uses a long stacked draft-PR chain; it is evidence of planned/authored state, not equivalent to merged `main`.

## GOV-M01 acceptance

- seven repositories inventoried;
- default branches and SHAs recorded;
- active PR and Issue surfaces recorded;
- major roadmap/policy entrypoints recorded;
- available CI/release evidence recorded;
- feature branches explicitly treated as non-canonical until accepted.
