# Haversine governance compatibility review — read-only

Reviewed 2026-11-18 from `DaniilSydorenko/haversine-geolocation`
`master`: root `AGENTS.md` and `docs/engineering/round-protocol.md`.
This is a **proposal**, not a Haversine repository modification or
adoption/approval.

## Compatibility decision: CONDITIONAL / no rollout yet

| Topic | Local Haversine authority | Safe central adoption |
| --- | --- | --- |
| Default branch | `master`, accepted HEAD only | Never assume `main`; distinguish Draft PR from accepted HEAD |
| Delivery process | Mandatory **12-step** engineering round, even for blocked/no-change work | Governance adds visibility; cannot replace, shorten or skip any step |
| Source of truth | `docs/roadmap/haversine-v2-human-roadmap.md` | Use existing roadmap; **no second status database** |
| Task queue | `docs/roadmap/haversine-v2-agent-rounds.md` | Reuse task IDs; do not create duplicate issues |
| Reviews and checks | All open PR paths, exact-head CI, applicable tests | Additional fast checks cannot replace local full validation |
| Publication | Maintainer gates for npm, releases, secrets, branch protection | No new permissions or automated release |
| Agent routes | Manual, owner-gated Cursor discovery; GitHub Autopilot separate | Governance is not an agent dispatcher or scheduler |
| External HQ | Read-only reference; HQ enforcement needs separate owner decision | Adoption is opt-in and locally reviewed |

## Proposed smallest local change (NOT executed)

After central #166 is accepted, add a **short additive section** to the
existing root `AGENTS.md`, not a replacement:

> ## AI engineering delivery visibility (local opt-in)
>
> Use the central AI Engineering Delivery Governance for short owner-facing
> reporting, evidence-backed blocker tracking, and AI-session estimates.
> Haversine's mandatory 12-step engineering round, canonical V2 roadmap,
> `master` acceptance, complete PR collision review and maintainer gates
> remain controlling. This does not enable a scheduler, paid agent, cross-repo
> writer, merge, npm release or branch-protection change. On new sessions
> restore Haversine's local sources first and independently verify current
> issue/PR/CI evidence.

No CI/ruleset changes are needed merely to propose a text-only local
adoption. **Operational enforcement** would require a separate, explicitly
scoped Haversine decision and tests.

## Stop / next action

STOP before a Haversine PR while central governance is Draft and domain
writer/collision review is incomplete. On authorized rollout: verify
Haversine current `master` SHA, all open PR paths, local owner approval and
12-step round evidence, then make one small repo-owned PR. Never mark
`ENFORCED` from an AGENTS.md pointer alone.
