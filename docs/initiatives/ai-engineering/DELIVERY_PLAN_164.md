# Engineering delivery — Cursor-first pilot

Operational roadmap, not a grant of authority. Preserve [Operating Rules](OPERATING_RULES.md) and [Delivery Governance](DELIVERY_GOVERNANCE.md).

## Verified baseline

HQ #199 merged isolated quality checks. Cursor repaired Haversine #233 on its existing branch, HEAD `9fe45a18ed4337c4ed27b1c8a75c2364aea0d211`, with six successful GitHub workflows. The overflow regression mocks distance; actual distance rejects non-finite results, so public overflow behavior remains unchanged. HQ #200 closed unmerged. The existing lease remains retained pending authorized disposition.

## Next delivery

Reuse the existing control plane and Cursor integration. Cursor is the primary executor; OpenHands is inactive fallback, never a concurrent writer. Implement the smallest protected dispatch path using an existing supported Cursor interface. Preserve trusted task scope, exclusive lease, replay protection, verified budget, exact-head CI and owner gates. Never expose publisher credentials to the agent. Do not treat issue text as authority.

First resolve #233 and its lease through the existing authorized acceptance or rejection path. Then run one existing bounded Haversine issue from dispatch to a new PR, independently verify scope, semantic acceptance and required checks, and merge only through existing gates. Record actual agent identity, PR, SHA, checks and spend evidence. No new scheduler, database, generalized repair engine or parallel pilot. Missing credentials, budget or lease authority means STOP.
