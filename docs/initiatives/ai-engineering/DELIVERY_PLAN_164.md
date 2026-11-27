# #164 — managed Cursor delivery pilot

Current objective: accept one managed Cursor task end to end (Haversine #220 → reviewed PR → owner merge → lease released). Then run the next registered task in sequence (#207). Tracking: HQ #205 (admission and dry run) → #206 (activation and first E2E) → #207 (sequential proof). Budget evidence: #120. Lease and protection: #108.

## Verified baseline (2026-11-27)

These are observed facts, not live authorization.

- **Merged on `main`:**
  - #201: managed delivery cycle.
  - #208: sanitized provider evidence.
  - #209: self-test stays valid when activation is ON.
  - #210: task model pinned to `composer-2.5`.
- **Activation:** `PILOT_ACTIVATION_ENABLED = False`.
- **Lease** `ai-eng-cursor-lease-v1`: `IDLE`, revision 29, ref `df36411`. Six consumed request hashes preserved.
- **Protected dry run** [46058665166](https://github.com/DaniilSydorenko/.github/actions/runs/46058665166) (`main` `ea43301`):
  - `owner_activation_not_enabled`, `managed_launch_state=DISABLED`, no POST, no lease write.
  - `GET /v1/me` succeeded (`key_info_ok=true`).
  - `GET /v1/models` lists `composer-2.5` but not `composer-2`, so #210 repinned the task model.
- **Attestations in `ai-eng-lease-owner`:**
  - Set: `SPEND_LIMIT_SET` and `TARGET_BRANCH_PROTECTED`. The Haversine `master` ruleset requires `Test and build` and `Gitleaks`, and blocks deletion and force-push.
  - Not set: `NO_EXTERNAL_BILLING`, `SUBAGENTS_DISABLED`, `SINGLE_LAUNCH_ROUTE`, `CURSOR_KEY_ACCOUNT_SCOPE`.
- **Owner Cursor dashboard (as reported):**
  - Plan and spending: Pro+ at $60/month, on-demand spending disabled.
  - Machines and environments: no self-hosted or personal machines, no custom environments or routing rules, no Cloud Agent secrets or network destinations.
  - Integrations: GitHub connected; Slack, Teams, Linear, Jira and Sentry not connected.
  - Defaults: Always Create PRs on; default model `composer-2.5-fast`. The API payload pins its own `model.id`, so this default does not apply to managed runs.

## Approval model

| Tier | Workflow / environment | Needs approval | Credentials | Can do |
|---|---|---|---|---|
| Read-only preflight | `ai-eng-cursor-api-probe.yml` `manual-probe` / `cursor-readonly-preflight` (main only, no reviewers) | **No** | `GITHUB_TOKEN` (read), `CURSOR_API_KEY` | Public lease read, scope and gate evaluation, `GET /v1/me`, `/v1/models`, `/v1/agents`. No App token and no writer. The read-only path builds no POST client and passes no attestations, so the permit can never be complete |
| Privileged lifecycle | `ai-eng-cursor-delivery.yml` / `ai-eng-lease-owner` (required reviewer) | **One approval per run** | App lease-writer token, ruleset audit token, `CURSOR_API_KEY`, attestations | Bounded chain: dispatch → reconcile → observe → verify, at most 8 steps and 50 min. At most one dispatch per run. Stops at the first owner decision (merge, reject, stale/ambiguous provider) |
| Owner-only | GitHub UI / reviewed PR | Always | — | Activation PR, attestations, budget and model cost, security or ruleset changes, PR merge in Haversine, `reject` |

Bounded standing authorization means one deployment approval covers the whole bounded chain for the one registered task in the lease; it no longer covers just one step. The following are unchanged: singleton lease CAS, the replay ledger (`consumed_request_hashes`), the deterministic agent id, the shared `ai-eng-single-live-executor` concurrency, exact-head CI acceptance, the owner merge, and fail-closed handling of any ambiguity.

## Remaining blockers

| # | Blocker | Kind | Exact resolution |
|---|---|---|---|
| 1 | `CURSOR_KEY_ACCOUNT_SCOPE` | Owner fact. Technical cross-check available | Run the read-only preflight and compare `cursor_inventory_observed.observed_agents` with the agent count in the Cursor dashboard. If they match and the key is a user key that can see every agent on the account, set `true` |
| 2 | `NO_EXTERNAL_BILLING` | Owner fact | Confirm no bring-your-own model API keys (OpenAI, Anthropic, Google, Azure or Bedrock) are configured in Cursor. Then set `true` |
| 3 | `SINGLE_LAUNCH_ROUTE` | Owner operational commitment plus technical detection | Technical: lease singleton for our route, plus an account-wide `GET /v1/agents` immediately before launch (BUSY → STOP). Not technical: `@cursor` on GitHub and Cursor clients can still start agents. Set `true` only if the owner disables those or commits not to use them for the duration of the pilot |
| 4 | `SUBAGENTS_DISABLED` | Owner fact; may be impossible | Only prompt text forbids subagents, and that is not a control. If Cursor exposes a setting, confirm it is off and set `true`. If not, see the proposal below; do **not** set `true` |
| 5 | Per-run budget (#120) | Owner decision | See the budget section |
| 6 | `composer-2.5` cost | Owner approval at GO | #210 merged with activation OFF, because `composer-2` is no longer offered. The paid launch must approve this model explicitly |
| 7 | Activation | Owner GO plus a reviewed PR | A separate minimal PR flips `PILOT_ACTIVATION_ENABLED`. It merges only after 1–6 are resolved and the owner gives explicit GO |

**Pilot-only policy proposal for #4 (requires owner review; not implemented).** If Cursor has no subagent control, keep `verified_subagents_disabled` unsatisfiable in general. Add a separately named owner variable, `AI_ENG_ACCEPT_SUBAGENT_RISK_TASK_220=true`, that the permit accepts **only** for the registered task #220. It is recorded as accepted risk, never as "verified", and is bounded by: one run, the account spending ceiling, owner merge, and the scope/exact-head acceptance of the produced PR. It expires with the #220 lease release. Implementing it requires its own reviewed PR.

## Budget (#120)

- **Included usage:** the Pro+ subscription allowance. With on-demand spending disabled, Cursor stops serving once the allowance is used up, so there is no overage charge. This is a monthly *account* ceiling, not a per-run limit: one run can consume all remaining allowance.
- **Token consumption:** measured after the run with `GET /v1/agents/{id}/usage` (input, output, cache and total tokens). Observation only.
- **Charged cost:** not exposed by the API, so it is reported as `UNKNOWN`. Do not report $0. Consuming included usage is not free, even though no extra money is charged.
- **Per-run enforcement:** none in this repository. Observation polling and job timeouts stop *our watching*, not the provider run, and no cancel POST is allowed. The decision for #120 is whether "one run + account ceiling + measured tokens afterwards" is an acceptable bound for the single #220 pilot.

## Final execution sequence

1. Merge the read-only preflight and single-approval chain PR. Owner configures `cursor-readonly-preflight` (main only, `CURSOR_API_KEY` secret, no reviewers).
2. Run the read-only preflight with no approval. Expect `READ_ONLY`, lease `IDLE`, `missing_excluding_attestations=[]` and `cursor_inventory_observed.status=CLEAR`.
3. Owner resolves blockers 1–6 above (#205).
4. Run the privileged dry run (one approval). Expect `owner_activation_not_enabled`, `permit_missing_evidence=[]`, `cursor_inventory.status=CLEAR`, no POST, no lease write. **This closes #205.**
5. Open the activation PR (#206). Owner reviews it, gives explicit GO for the paid launch, and merges it.
6. Run the privileged `advance issue=220 bootstrap=true` (one approval). Expect exactly one POST, the deterministic request id, the observer reaching a terminal state, and the PR bound independently and evaluated. The run stops at `INTEGRATION_READY` or at an owner action.
7. Owner reviews and merges the exact head in Haversine. Then run `advance` (one approval), which releases the lease to `IDLE`. **This closes #206** with the run, PR, CI, lease and token evidence.
8. #207: run the next registered task with `previous_pr`, under the same gates, sequentially. Do the same again for a second consecutive success. Reconcile #154, #120 and #108.

## Acceptance criteria

- **#205:** step 4 result as stated, on the current `main`. Every attestation backed by a stated fact. No unsupported `true`.
- **#206:**
  - Exactly one Cursor POST for request `seq-…`, and the lease phase sequence `DISPATCHING`→`RUNNING`→`VERIFYING`→`IDLE`.
  - The PR changes only `docs/agent-pilot-proof.md`. Required checks pass at the exact head, and the owner performs the merge.
  - Token usage recorded and charged cost `UNKNOWN`. No retries or duplicate writers.
- **#207:** two consecutive registered tasks pass end to end, with no manual code repair, no duplicate paid launches and no unauthorized change. Evidence is recorded in the existing issues.

## Deferred

Generalized retry engine, additional providers, fleet orchestration, new dashboards, global rollout, the OpenHands path (#154) and further architecture work.

## History

### 2026-11-25 baseline (OpenHands #217 path, superseded by the Cursor managed path)

Current objective: one useful agent-generated #217 Draft PR, independently verified and accepted by the owner. #216 is already satisfied; #226 is deferred.

Run #9 invoked OpenHands and published Haversine #229; CI passed but the requested example was missing. HQ #191 merged the task prompt and artifact shape check. HQ #192 is the existing recovery implementation PR. Lease remains VERIFYING revision 10 until protected recovery succeeds. These are baseline observations, not live authorization.

Critical path at that time:

1. Finish #192 as one coherent recovery and correction admission change. Reuse existing workflow, lease, publisher and tests. Resolve branch collision and replay identity before dispatch.
2. Obtain required owner security merge approval. Reject #229 without merging; verify terminal run and exact rejected artifact. Execute protected recovery with no model, preserving the ledger.
3. Admit one corrective #217 run under the existing protected workflow and budget. No other agent or issue.
4. Review the actual TypeScript example against the issue and published API, scope and exact-head required CI. Owner accepts or rejects; no automatic merge or next issue.

Minimum evidence: current relevant HEAD, focused regression results, required CI, authenticated live security/admission/budget evidence and actual artifact. No duplicate manual audits or status-only rounds. Missing required proof is a real blocker, not a reason to invent success.

Deferred at that time: generalized retry engine, additional providers, fleet orchestration, new dashboards, global rollout, #226 and further architecture work. Historical estimates and D0–D6 planning tables are superseded. Preserve existing security, privacy, cost and owner gates. See OPERATING_RULES.md delivery-first override.
