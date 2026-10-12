# Engineering Source-of-Truth Index

Status: ACTIVE DISCOVERY INDEX
Date: 2026-10-12

GitHub is the canonical home for accepted engineering artifacts across the governed repositories. This file is the human-readable entrypoint; `governance/repository-registry.json` is the machine-readable discovery index.

This index does **not** copy live progress. It tells agents and maintainers where the actual local source of truth lives.

## Global order

1. Read the repository entry in `governance/repository-registry.json`.
2. Read the repository's declared local roadmap / specialized trackers.
3. Read local agent/authority rules when present.
4. Inspect the current default branch, open PRs, Issues and relevant CI before mutation.
5. Treat open PRs/feature branches as proposed evidence until accepted merge.
6. Use runtime/scheduler platforms as authority for live runtime state where applicable.
7. Use chat memory only as context, never as proof.

## Status ownership

- Roadmap: milestones and priorities.
- Issues: independently actionable defects, blockers and deferred work when coordination value exists.
- PRs: implementation and acceptance evidence.
- Reports: read-only reconciliation, not an independent task-status owner.
- Runtime/scheduler state: external live authority where the repository contract says so.

One concern should have one mutable status owner. Other surfaces reference it.

## Repository discovery

| Repository | Canonical branch | Primary roadmap/source | Agent / authority entrypoint |
|---|---|---|---|
| `.github` | `main` | `reports/github-hq/ROADMAP-LIVE.md` | HQ/Autopilot boundary + GRS operating model |
| `autopilot-control-plane` | `main` | `ROADMAP.md` | `AUTHORITY.md` / `CONTROL_PLANE.md` |
| `listing-kit` | `main` | `ROADMAP.md` | `AGENTS.md` |
| `career-intelligence` | `main` | `docs/PLATFORM_ROADMAP_V2.md` | existing `AGENTS.md` + worker policy; specialized public trackers remain separate |
| `engineering-handbook` | `main` | `handbook/00-canonical-toc.md` | Git-content authority ADR + automation architecture |
| `engineering-labs` | `main` | `docs/tasks/00-STATUS-DASHBOARD.md` | `AGENTS.md` + ecosystem manifest |
| `haversine-geolocation` | `master` | `docs/roadmap/haversine-v2-human-roadmap.md` | architecture index + GRS manifest |

## Local specialization is intentional

The registry standardizes discovery, not file layout.

ListingKit intentionally keeps separate product roadmap, execution status, MVP readiness and Foundation E design responsibilities. Career Intelligence keeps platform/public/assistant sub-roadmaps. Handbook and Labs use machine-readable manifests for theory/practice integration. Haversine keeps its own human roadmap and release history.

Do not flatten these into one universal tracker.
