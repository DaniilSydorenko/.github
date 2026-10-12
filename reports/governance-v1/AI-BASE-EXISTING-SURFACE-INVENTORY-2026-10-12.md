# Engineering Governance v1 — AI BASE Existing-Surface Inventory

Date: 2026-10-12
Status: COMPLETE for the observed checkpoint
Purpose: inventory before proposing any shared AI/agent contract.

## Rule

AI BASE must stay tiny. Reuse existing repository guidance, worker policies, Cursor rules and CI. A shared contract should define only cross-repository minimums that cannot already be discovered locally.

## Seven-repository inventory

| Repository | Existing agent / tool surfaces | Existing CI / validation | Material observation |
|---|---|---|---|
| `.github` | central GRS/governance docs; no root AGENTS.md required | Autopilot Help, GRS Control Plane, reusable Autopilot health | already the global governance source; do not add a parallel agent framework |
| `autopilot-control-plane` | CONTROL_PLANE.md, AUTHORITY.md, FLEET.yaml, local policies; no generic root AGENTS.md needed for current model | validate, reconcile, issue-sync, roadmap-executor, weekly review, Autopilot Help | runtime/control-plane rules are already specialized and should remain local |
| `listing-kit` | root AGENTS.md, `.autopilot/worker-policy.md`, extensive `.cursor/rules/*` | CI, Secret Scan, Autopilot Help | richest existing AI surface; shared Governance v1 must not duplicate or flatten it |
| `career-intelligence` | root AGENTS.md, `.autopilot/worker-policy.md`; AGENTS.md currently mainly protects Lovable history | validate, Secret Scan, Autopilot Help | discovery gap is real, but extension should reuse the existing file or registry pointers rather than add a second framework |
| `engineering-handbook` | `.autopilot/worker-policy.md`; no root AGENTS.md observed on canonical main | Handbook Validate, Secret Scan, Autopilot Help | discovery gap exists; first prefer registry pointer to existing canonical docs/policy before inventing a new mandatory file |
| `engineering-labs` | root AGENTS.md, app-local AGENTS.md, `.autopilot/worker-policy.md`, `.cursor/rules/*`, `docs/CURSOR_RULES.md` | Quality, Secret Scan, Autopilot Help | already has a strong layered agent model; preserve it |
| `haversine-geolocation` | no general AGENTS.md / Cursor layer observed | CI, GRS, Secret Scan, compatibility, benchmarks, consumer fixtures, release workflows | simple OSS repo does not currently justify an AI framework; governance discovery can rely on roadmap/GRS/CI pointers |

## Findings

1. A universal copied `AGENTS.md` would be wasteful and would create drift.
2. Cursor-specific guidance is useful only where Cursor is actually used; ListingKit and Labs already have mature local adapters.
3. Worker policy files already exist for ListingKit, Career Intelligence, Handbook and Labs. They are specialized execution contracts and should not be replaced by Governance v1.
4. CI is already the strongest shared evidence surface across all seven repositories.
5. The minimum shared AI BASE should therefore be discovery + authority + evidence semantics, not a universal prompt/rules package.

## Minimal AI BASE proposal

If approved later, the shared layer should contain only:

- identify canonical repository/default branch;
- discover local roadmap / specialized trackers through registry pointers;
- discover local agent/worker guidance when present;
- honor domain ownership and owner gates;
- inspect live PR/CI state before mutation;
- distinguish implemented/tested/merged/deployed/released/runtime-verified;
- stop on ambiguous authority or changed exact head.

Tool-specific adapters remain local and optional.

## Explicit non-goals

- no universal prompt framework;
- no mandatory Cursor config;
- no shared hook system;
- no copied skill bundle;
- no extra scheduler;
- no AI-specific database/service;
- no requirement that every repository have the same files.

## Acceptance

The inventory is sufficient to prevent premature AI BASE construction. Any future shared contract must justify each new cross-repository rule against this inventory and prefer a pointer to existing local guidance.
