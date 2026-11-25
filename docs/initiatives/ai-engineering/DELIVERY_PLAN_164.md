# #164 — delivery-first pilot

Current objective: one useful agent-generated #217 Draft PR, independently verified and accepted by the owner. #216 is already satisfied; #226 is deferred.

## Current baseline (2026-11-25)

Run #9 invoked OpenHands and published Haversine #229; CI passed but the requested example was missing. HQ #191 merged the task prompt and artifact shape check. HQ #192 is the existing recovery implementation PR. Lease remains VERIFYING revision 10 until protected recovery succeeds. These are baseline observations, not live authorization.

## Critical path

1. Finish #192 as one coherent recovery and correction admission change. Reuse existing workflow, lease, publisher and tests. Resolve branch collision and replay identity before dispatch.
2. Obtain required owner security merge approval. Reject #229 without merging; verify terminal run and exact rejected artifact. Execute protected recovery with no model, preserving the ledger.
3. Admit one corrective #217 run under the existing protected workflow and budget. No other agent or issue.
4. Review the actual TypeScript example against the issue and published API, scope and exact-head required CI. Owner accepts or rejects; no automatic merge or next issue.

## Minimum evidence

Current relevant HEAD, focused regression results, required CI, authenticated live security/admission/budget evidence and actual artifact. No duplicate manual audits or status-only rounds. Missing required proof is a real blocker, not a reason to invent success.

## Deferred

Generalized retry engine, additional providers, fleet orchestration, new dashboards, global rollout, #226 and further architecture work. Historical estimates and D0–D6 planning tables are superseded. Preserve existing security, privacy, cost and owner gates. See OPERATING_RULES.md delivery-first override.
