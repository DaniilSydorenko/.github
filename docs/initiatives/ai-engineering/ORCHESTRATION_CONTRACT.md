# AI Engineering — One-Repository Orchestration Contract

**Status:** OWNER-REVIEW DRAFT / NON-ENFORCING / NOT WIRED TO AUTOMATION  
**As of:** 2026-10-24 · **Baseline `main`:** `d340d9fe3beaccd02e54065f0108c3e3d73e520e`  
**Owner:** Daniil · **Scope:** initiative coordination guidance in `DaniilSydorenko/.github` only  
**Related:** [Operating Rules](OPERATING_RULES.md) · [Roadmap](ROADMAP.md) · [Decision Gate](DECISION_GATE.md) · [HQ/Autopilot Boundaries](../../../reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md) · [AGENTS.md](../../../AGENTS.md)

This document defines **how** ChatGPT-side AI Engineering work is selected, reviewed, and dispatched. It is **not** a second control plane, scheduler, or substitute for domain authorization. Issue #118 authorizes preparation of this draft only.

## Four roles — do not conflate them

| Role | Repository / system | What it owns | What this contract does **not** grant |
| --- | --- | --- | --- |
| **Initiative coordinator** | `DaniilSydorenko/.github` → `docs/initiatives/ai-engineering/` | Owner-facing selection, preflight, evidence review, bounded `@cursor` dispatch **when separately authorized** | Write access, merge authority, or PR backlog management in domain repos |
| **GitHub HQ infrastructure** | Same `.github` repo (GRS, shared workflows, HQ roadmap) | Shared GitHub foundation per [HQ-AUTOPILOT-BOUNDARIES](../../../reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md) | Domain product implementation, cross-repo PR triage, or fleet enforcement |
| **Autopilot Control Plane** | `autopilot-control-plane` (scheduled workers) | Fleet health, telemetry, bounded Class A/B maintenance in **worker-owned** surfaces | Initiative orchestration, ChatGPT memory, or Cursor account control |
| **Domain owner** | Each product repo (Haversine, Ladvero, Career, Handbook, Labs, etc.) | Canonical roadmap, `AGENTS.md`, CI, merge/release, data boundaries | Automatic delegation because a central Issue exists |

Choosing **one coordination repository** for AI Engineering does **not** imply blanket consent to mutate every target repository.

## Owner-facing decision surface

1. **Central surface (this repo):** Issues such as #118 record owner goals, acceptance criteria, and orchestration policy. ChatGPT may inspect/create **authorized** tasks here and link to domain evidence.
2. **Domain surface (target repo):** Implementation truth stays in the owning repository — its Issue/PR, default branch, required CI, and owner gates. A domain Issue/PR is still required when code or repo-local policy must change there.
3. **No shadow authority:** A coordinator Issue is **not** a secret substitute for domain owner approval or a Cursor executable in another repo without an explicit, scoped dispatch comment on that repo's Issue/PR.

## Control flow (manual today; automation NOT VERIFIED)

```
Owner goal (ChatGPT or Issue)
  → Fetch ONLY relevant domain authority + current default SHA + linked Issue/PR heads
  → Build attested snapshot (optional: offline classifiers below)
  → Classify → owner single opt-in to dispatch
  → Cursor Cloud Agent in authorized target repo/branch/paths only
  → Focused tests + exact-head required CI (never substitute PR CI for post-merge)
  → Owner/domain-controlled merge (default: owner-gated for this initiative)
  → Accepted-main / release / device evidence as separate states
```

**Classification labels** (orchestration vocabulary; map to [Decision Gate](DECISION_GATE.md) verdicts where applicable):

| Label | Meaning | Default action |
| --- | --- | --- |
| `ALREADY_ACCEPTED` | Same outcome already on default branch | Reconcile Issue; no repeat coding |
| `EXISTING_PR` | Open PR already attempts outcome | Continue **that** PR; no second writer |
| `READY` | Bounded, evidenced **candidate**; no observed collision | Owner opt-in → one scoped `@cursor` dispatch |
| `WAITING_DEPENDENCY` | Stacked base, overlap, or active writer | Record blocker; pick other authorized work or wait |
| `OWNER_GATE` | Permission, private data, publication, billing, merge | One precise owner question; STOP |
| `UNSAFE` | Forbidden scope (secrets, destructive, learner-owned, cross-repo without auth) | STOP; report |
| `NO_READY_WORK` | No eligible task after preflight | Valid stop; not a retry loop |

`NEEDS_EVIDENCE`, `SUPERSEDED`, and `EXTERNAL_BLOCKED` from the decision gate remain in use for stale snapshots and provider gaps; treat them as fail-closed (no dispatch).

## Verified vs proposed (Pilots 01–03)

**VERIFIED today (Haversine pilots):** ChatGPT → GitHub Issue/comment → `@cursor` launch; Cursor reads scoped files; completion via `cursor[bot]`; bounded code fix with exact-head CI; owner-authorized squash merge; one PR follow-up on same branch/session (Pilot 03). See [Roadmap](ROADMAP.md) for SHAs and limits.

**NOT VERIFIED / OWNER GATE for orchestration:** automatic task queues; cross-repo dispatch from a single coordinator comment; technical branch lease across desktop+cloud; agent-native GitHub `addComment`; post-merge CI via connector; self-correction loops (Pilot 04); Ladvero/multi-repo chains; any wiring of classifier exit codes to `@cursor`, merge, or Control Plane workers.

State/ETA rule: report `UNKNOWN` or `BLOCKED` when proof is missing; never treat green workflow alone as merge, release, or deployment acceptance.

## Consumption of accepted initiative assets (post-merge)

Do **not** duplicate canonical strategy or gate logic. After owner review/merge, this contract **references**:

| Asset | Origin | How orchestration uses it |
| --- | --- | --- |
| Roadmap v2 | Merged #111 → [ROADMAP.md](ROADMAP.md) | Phase/gate vocabulary; pilot evidence; not re-copied here |
| Decision Gate | Merged #112 → [DECISION_GATE.md](DECISION_GATE.md), `decision_gate.py` | Offline advisory classifier for **one** task snapshot; exit code ≠ dispatch permission |
| Low-Burn rules | Merged #113 → [OPERATING_RULES.md](OPERATING_RULES.md) | Every dispatch: one writer, max two evidence-based corrections, no subagents |
| Agent entry | Merged #114 → [AGENTS.md](../../../AGENTS.md) | HQ repo agent preflight; domain repos keep their own `AGENTS.md` |
| Provenanced evidence | Issue #116 (open research) | Future: stricter attestation envelopes — **NOT VERIFIED** until accepted |
| Issue↔PR reconciliation | Issue #117 (open research) | Future: semantic matching guidance — human/connector today |

No new database, scheduler, queue, monitor, or mandatory per-repo manifest is introduced by this contract.

## Hard boundaries (fail-closed)

- **One active writer** per branch/PR; no parallel cloud+desktop without pushed handoff and fresh HEAD.
- **No automatic merge, release, npm publish, visibility, secrets, billing, or scheduler changes.**
- **No unauthorized cross-repo mutation** — each Cursor run's `repository`, `allowed_paths`, and `baseline_sha` must be explicit ([Operating Rules](OPERATING_RULES.md) YAML block).
- **No unlimited agent chains** — finishing one Issue does not authorize the next; no standing "follow all open Issues."
- **HQ infra only** when the target is `.github`; product work stays in the product repo with domain owner gates.
- **Control Plane** remains health/telemetry for scheduled workers; initiative ChatGPT/Cursor flows do not reconfigure it.
- **Private/customer data:** ingestion or production private sources → `OWNER_GATE` / `UNSAFE`; public-safe coordination text only in this repo.

## Owner safety mode — no unattended execution (2026-10-25)

**Current authorization = MANUAL ONLY.** Owner wants future one-at-a-time continuation, but this draft **does not** enable it. Until the safeguards below are observed and tested, do not turn on Cursor Project subscriptions, schedules, event-based dispatch, unattended retries, cross-Issue chaining, or auto-merge. A prompt, `AGENTS.md`, Markdown budgets, and a shared session ID are **not hard enforcement**.

- **Cost:** verify the actual current individual Cursor account plan and **provider-enforced On-Demand Spending = Disabled** (last owner observation 2026-10-22). Never enable pay-as-you-go, paid top-up, unlimited overages, model upgrades, or billing changes. Provider/account limits are the protection against extra billing; instructions alone are not. Included tokens remain finite. If provider controls, spend attribution, or behavior are UNKNOWN, **STOP; do not launch unattended work**.
- **One execution:** exactly **one actively running model-consuming engineering execution across all authorized triggers** (including coordinator/delegates, desktop/cloud, retry and subscription wake-up). Before future autonomy, independently demonstrate **atomic, shared, fail-closed concurrency/idempotency control** across trigger sources and prove a second attempted start is rejected. Inability to enforce this is a **hard blocker**; do not claim Cursor Projects naturally supplies a one-agent lock.
- **Sequence:** use **only** existing owner/domain-approved roadmap tasks and verified Issue/PR links. Next task starts only after the previous one has reached its specified **accepted** state (or is explicitly released/blocked and the owner pre-authorized an independent leaf). PR open, agent finish, green CI, or Issue close alone is not product/release acceptance. No self-generated work backlog, surprise Issues, or unapproved scope expansion.
- **Finite attempts:** one implementation with at most two distinct evidence-based corrections. A CI or PR subscription is a **potential paid model wake-up**; default auto-fix, recurring subscriptions, and Projects multiagent delegation remain OFF until the owner accepts observed bounds and stop conditions.
- **Owner stops:** merges/releases/publication, secrets/private data, permissions, subscriptions/worker/scheduler setup, model/billing changes, destructive actions and policy changes remain human gated. Lack of permission/lease/provenance/checks/cost visibility → `OWNER_GATE` / `NEEDS_EVIDENCE` / `STOP`, never optimistic READY.
- **Evidence required before autonomous promotion:** provider/account screen for spending controls; negative test of second concurrent start; duplicate webhook/retry test; stale SHA and existing-PR reuse; budget exhaustion/denial; agent STOP on ambiguous authorization; measurable token usage; no unapproved merges. Record only sanitized acceptance in the existing owning Issue/PR. Owner must explicitly approve any later enablement.

## Event-driven cross-team handoff (only on a concrete dependency)

When AI Engineering needs an HQ infrastructure change (or HQ needs an initiative-local contract change), use a **single comment on the existing owning Issue/PR** with `OWNER`, `REQUEST`, `IMPACT`, `EVIDENCE` (specific Issue/PR, exact SHA, checks), and `ACCEPTANCE`. Receiver replies with decision and accepted commit/check in **that same thread**. No duplicated roadmap, status polling, new Issue by default, or automatic coordination between chats. Each team keeps exclusive write/merge authority for its own files and PRs; absent a real dependency, **no handoff**.

## Illustrative acceptance matrix (synthetic decisions)

| Case | Preflight observation | Classification | Safe decision |
| --- | --- | --- | --- |
| **(a) READY public-safe fix** | Domain `main` SHA fresh; scoped Issue; no overlapping open PR on same paths; owner commented YAML dispatch on **domain** Issue; `owner_permission: true` | `READY` | Owner opt-in → single `@cursor` in **target repo**; report exact-head CI; STOP for merge |
| **(b) Overlapping / stale PR** | Same paths changed in open PR #X; task default SHA ≠ live `main` | `EXISTING_PR` or `NEEDS_EVIDENCE` | Review/continue PR #X; refresh SHA; **no** second branch |
| **(c) Owner-gated / private data** | Task requires private corpus or publication decision | `OWNER_GATE` or `UNSAFE` | One owner decision; no agent until scope is public-safe and authorized |
| **(d) Two writers / device handoff** | Cloud agent active on branch; desktop unpushed edits | `WAITING_DEPENDENCY` | STOP; require push + single writer; branch lease **NOT VERIFIED** as automatic |

Each negative row **must** stop dispatch; classifiers and connectors do not override missing permission.

## Dispatch minimum (when `READY` and owner opted in)

Reuse the [Operating Rules](OPERATING_RULES.md) scoped-dispatch YAML: `task_id`, `repository`, `owner`, `baseline_sha`, `goal`, `read_first`, `allowed_paths`, `forbidden_paths`, `required_checks`, `max_evidence_based_corrections: 2`, `deliverable`. Post on the **authorized domain Issue/PR**, not only on coordinator #118.

Optional preflight: run `python3 -m unittest discover -v -p 'test_*.py'` under `docs/initiatives/ai-engineering/` when touching gate code; for coordination-only docs, N/A.

## Owner decision required (Issue #118)

Choose **one**:

1. **Guidance only** — Accept this contract as initiative coordination documentation. ChatGPT continues manual preflight and owner-opt-in dispatch; no automatic cross-repo delegation from coordinator Issues.
2. **Future execution** — Additionally approve narrowly scoped agent execution patterns (named repo, path class, and trigger), each still requiring per-task owner opt-in and domain Issue/PR linkage until a separate standing rule is explicitly defined.

**This Issue does not**, by itself, authorize orchestration automation, Control Plane changes, or merges. Owner review and controlled merge of this PR are required before treating the contract as accepted guidance.

---

*Completion evidence for this draft belongs on the implementing PR: head SHA, changed paths, applicable CI (docs-only: N/A if no workflow), cost UNKNOWN unless provider-measured.*
