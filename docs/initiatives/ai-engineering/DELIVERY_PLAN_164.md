# #164 — managed Cursor delivery pilot

Current objective: accept one managed Cursor task end to end (Haversine #220 → reviewed PR → owner merge → lease released). Then run the next registered task in sequence (#207). Tracking: HQ #205 (admission and dry run) → #206 (activation and first E2E) → #207 (sequential proof). Budget evidence: #120. Lease and protection: #108.


## Operational completion checklist

The canonical status, kept in sync with GitHub. The [owner-approved roadmap](https://github.com/DaniilSydorenko/.github/issues/207#issuecomment-7231706196) is frozen. Operating mode: **Maximum Safe Throughput** (see `AGENTS.md`). Status legend: implemented / offline-tested / merged / live-verified / blocked / deferred.

| Phase | Issue | Status (2026-11-28) | Next action |
|---|---|---|---|
| 0: Engineering infrastructure (pilot) | #205, #206, #207 | **accepted**: 2 managed tasks integrated, lease `IDLE` r41, 8 replay hashes | none (reopen only on a real regression) |
| 1: Dynamic queue | #226 | part 1 **merged** (#227 `8a9a6ff`); part 2 **offline-tested, CI green, waiting for owner merge** (#228 head `56a0f4d`); public targets only | owner merges #228 → one live `submit-queue` and read-back (no POST) |
| 2: Automatic task preparation | #229 | not started; depends on #226 | read-only `prepare` in the probe |
| 3: Batch authorization and autonomous execution | #230 | not started; the approval-model change needs an owner decision | after #226 and #229 |
| 4: Auto-merge policy and bounded repair | #231 | not started; the policy needs explicit owner approval | after #230 |
| 5: Multi-repo, private control plane, latency, #120 | #232, #120 | **blocked**: `listing-kit` and `engineering-handbook` are private, and HQ is public. A private control plane is an owner decision | owner decision on the private control repository |
| 6: Control contract and private Control Center | #233 | not started; hosting and authorization design to be confirmed by the owner before provisioning | after #230 |
| 7: Final acceptance (5 LADVERO issues) | #234 | not started | after phases 1–6 |

**Confidentiality rule:** this repository, its refs and its Actions logs are public. Queue, lease and log data for private repositories must never be stored here (enforced in `cursor_queue` since #228).

## Current status (2026-11-28)

- **#205: closed.** The activation-OFF dry run [46081552315](https://github.com/DaniilSydorenko/.github/actions/runs/46081552315) had `permit_missing_evidence=[]`.
- **#206: accepted and closed.** The first managed Cursor task ran end to end:

| Stage | Evidence |
|---|---|
| Activation | #212 (`8fac491`) merged after owner GO #220 |
| Launch | [46087972278](https://github.com/DaniilSydorenko/.github/actions/runs/46087972278): exactly one dispatch; agent `bc-09b95ce8-e90c-5449-9dd5-209043eec6b3`, run `run-38ff24fb-c410-480b-9e75-3a3912d05131` |
| Fixes found live | #218: the provider omits `startingRef`, so ancestry is checked against the GitHub default head. #219: read-only token usage. #220: after a squash merge, a bound PR is checked against its GitHub `base.sha` (found before the owner merge) |
| Integration | [46090411782](https://github.com/DaniilSydorenko/.github/actions/runs/46090411782) `INTEGRATION_READY`; Haversine #234, exact head `9f1c199`, `docs/agent-pilot-proof.md` only, `Test and build` and `Gitleaks` green |
| Owner merge | squash `7760a2f` by the owner |
| Release | [46091661106](https://github.com/DaniilSydorenko/.github/actions/runs/46091661106) `RELEASED`, acceptance `INTEGRATED`; lease `IDLE` revision 35, seven replay hashes preserved |
| Tokens | input 110,474 / output 9,584 / cache read 613,568 / cache write 0 / total 733,626; charged cost `UNKNOWN` ([46090702636](https://github.com/DaniilSydorenko/.github/actions/runs/46090702636)) |

- **Not verified:** the model variant. `composer-2.5` was sent without `params`, so its default variant ran. The agent self-reports `composer-2.5-fast`, and the API exposes no field for the model actually used.
- **#207: accepted and closed (2026-11-28).** The second managed task, Haversine #235 (a V2 options-validation fix with Vitest regressions), ran end to end on the fixed infrastructure with **no repair**:
  - launch [46136598547](https://github.com/DaniilSydorenko/.github/actions/runs/46136598547): one approval, exactly one dispatch, through to `INTEGRATION_READY`;
  - PR #236, exact head `ed8f9a7`, the 3 allowed files, 10/10 checks green;
  - owner merge `0de9a82`;
  - release [46140091447](https://github.com/DaniilSydorenko/.github/actions/runs/46140091447) `RELEASED`; lease `IDLE` **r41**, 8 replay hashes;
  - tokens 1,377,248; charged cost `UNKNOWN`.
- **Reconciled:** #108 closed (lease rulesets active and read back); #154 closed as superseded by the Cursor path; #120 open with 2 of 3 measured runs. Both residual-risk variables are deleted.
- **Pilot milestone complete.** Next: operational completion Phase 1, the dynamic ordered queue ([owner-approved roadmap](https://github.com/DaniilSydorenko/.github/issues/207#issuecomment-7231706196)). Known item for Phase 1: the public, unauthenticated lease read can hit the runner rate limit (preflight [46138457389](https://github.com/DaniilSydorenko/.github/actions/runs/46138457389)); use an authenticated read.

## Admission baseline (2026-11-28, before #206)

These are observed facts, not live authorization.

- **Merged on `main`:**
  - #201: managed delivery cycle.
  - #208: sanitized provider evidence.
  - #209: self-test stays valid when activation is ON.
  - #210: task model pinned to `composer-2.5`.
  - #211: approval-free read-only preflight and single-approval lifecycle chain.
  - #214, #215, #216: sanitized inventory STOP detail, one retry of a read-only GET after a transport failure, and a 15-minute read-only job timeout.
- **`main`:** `6e6840ee3b4e9886c4c11c6390cb45ef561a3c50`.
- **Activation:** `PILOT_ACTIVATION_ENABLED = False`.
- **Lease** `ai-eng-cursor-lease-v1`: `IDLE`, revision 29, ref `df36411`. Six consumed request hashes preserved.
- **Protected dry run** [46058665166](https://github.com/DaniilSydorenko/.github/actions/runs/46058665166) (`main` `ea43301`):
  - `owner_activation_not_enabled`, `managed_launch_state=DISABLED`, no POST, no lease write.
  - `GET /v1/me` succeeded (`key_info_ok=true`).
  - `GET /v1/models` lists `composer-2.5` but not `composer-2`, so #210 repinned the task model.
- **Read-only preflight** [46072375294](https://github.com/DaniilSydorenko/.github/actions/runs/46072375294) (`main` `6e6840e`, no approval, success):
  - `READ_ONLY`, `key_info_ok=true`, `composer-2.5` offered.
  - Account-wide inventory `CLEAR`: `observed_agents=282`, `no_active_cursor_agents`.
  - `missing_excluding_attestations=[]`, `cursor_post_attempted=false`, lease `IDLE` rev 29.
  - The inventory takes about 5 minutes, because it reads the latest run of every non-archived agent.
- **Attestations in `ai-eng-lease-owner`:**
  - Set: `SPEND_LIMIT_SET` and `TARGET_BRANCH_PROTECTED`. The Haversine `master` ruleset requires `Test and build` and `Gitleaks`, and blocks deletion and force-push.
  - Set 2026-11-27 from owner statements: `NO_EXTERNAL_BILLING` (no BYOK or external model keys in Cursor) and `SINGLE_LAUNCH_ROUTE` (owner commitment: no parallel or manual launches during the pilot, plus technical BUSY detection).
  - Not set: `CURSOR_KEY_ACCOUNT_SCOPE` (evidence in hand, owner sets it) and `SUBAGENTS_DISABLED` (no verified provider control).
- **Owner decisions (2026-11-27):** `composer-2.5` approved. #120: one run within the subscription allowance, on-demand spending disabled, tokens measured, charged cost `UNKNOWN`, accepted. Neither is activation approval.
- **Subagent control investigation:** the Cloud Agents OpenAPI `CreateAgentRequest` has no field that disables or limits the built-in subagents (`explore`, `shell`, `debug`, `computerUse`, `cursorGuide`); `customSubagents` only adds more. An IDE setting and a `subagentStart` hook are reported on the Cursor forum. Neither is documented for API-launched Cloud Agents, and a hook would need a Haversine change outside #220's scope.
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
| 1 | `CURSOR_KEY_ACCOUNT_SCOPE` | **Resolved 2026-11-28** (owner set it) | Evidence: personal key created by the owner, on Pro+ (a single-user plan), with an account-wide list of 282 agents including archived ones (run 46072375294). Setting it is owner-only |
| 2 | `NO_EXTERNAL_BILLING` | **Resolved 2026-11-27** | Owner statement: no BYOK or external model keys. Set to `true` |
| 3 | `SINGLE_LAUNCH_ROUTE` | **Resolved 2026-11-27** | Owner commitment: no parallel or manual launches during the pilot. Technical detection: the account-wide inventory before launch (BUSY → STOP). Set to `true` |
| 4 | `SUBAGENTS_DISABLED` | **Resolved for #220 only** (#213 merged; owner accepted the risk) | No enforceable provider control is verified, so it stays unset. The accepted-risk mechanism for #220 only is ready in #213; the owner merges it and sets the variable only if they accept the risk |
| 5 | Per-run budget (#120) | **Resolved 2026-11-27** | Owner accepted one run within the subscription allowance; on-demand off, tokens measured, cost `UNKNOWN` |
| 6 | `composer-2.5` cost | **Resolved 2026-11-27** | Owner approved `composer-2.5` for the pilot |
| 7 | Activation | **Resolved 2026-11-28** (#212 merged after GO #220) | A separate minimal PR flips `PILOT_ACTIVATION_ENABLED`. It merges only after 1–6 are resolved and the owner gives explicit GO |

**Pilot-only residual-risk policy for #4 (implemented as a Draft PR; inert until the owner merges it and sets the variable).** If Cursor has no subagent control, `AI_ENG_ATTEST_SUBAGENTS_DISABLED` stays unset and `verified_subagents_disabled` stays `false` in every permit. A separate owner variable, `AI_ENG_ACCEPT_SUBAGENT_RISK_TASK_220=true`, waives that one gate **only** for the registered task (`DaniilSydorenko/haversine-geolocation` #220). The permit and the dispatch result record it as `accepted_residual_risks=["subagents_unblocked_accepted_task_220"]`, never as verified. No other gate can be waived, and the waiver cannot reach any other task, including #207. It is bounded by: one run (replay protection consumes the #220 request id), the account spending ceiling, owner merge, and the scope/exact-head acceptance of the produced PR. The owner deletes the variable after #206 closes.

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
