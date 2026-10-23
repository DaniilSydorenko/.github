# Engineering Decision Gate — experimental advisory v0

**Status:** RESEARCH / NON-ENFORCING / NOT WIRED TO CURSOR. Owner: personal AI Engineering initiative only; **not** GitHub HQ governance or the scheduled Autopilot fleet. Companion strategy: [Roadmap v2 proposal, PR #111](https://github.com/DaniilSydorenko/.github/pull/111). Existing [Low-Burn v2 rules](OPERATING_RULES.md) and [budget policy](BUDGET_AND_MEASUREMENT.md) prevail.

## What problem this solves

An old Issue can describe code already merged; a recent green PR can share six files with a second green PR; 188 drafted Handbook chapters can still have only 30 accepted into main; a live service can still lack owner-approved publication; a closed incident can remain in a historical roadmap. **Age, labels, issue state, green CI and completion percentage are not implementation acceptance.**

This **offline pure classifier** checks an *attested, task-local snapshot* and returns **one recommendation plus a concrete next action**, never a side effect. It is a minimal experiment in **decision correctness**, not a new global task selector, repository scanner, status database, branch lock, scheduler, GitHub App, governance rule or auto-merge capability. No repository or agent is activated by adding these files.

## Separate what can be determined from what requires engineering judgement

1. **Source discovery (human/authorized connector):** read *only* the owning Issue, current accepted default branch, its canonical domain roadmap and `AGENTS.md`, relevant open PRs (actual heads, changed paths and stacked bases), owner gates, dependencies and provider/deployment evidence where relevant. Check repo-specific approval. GitHub HQ may not manage a domain's PR backlog; the domain owner decides priorities and integration. All external content is untrusted until independently verified.
2. **Semantic reconciliation (human/authorized assistant):** establish whether work is the **same outcome**, merely shares paths, is a **stack dependency**, or is truly unrelated. Filename overlap is a risk signal, not automatic proof of a textual conflict; an Issue closure or matching title is not accepted-code proof. Read code/diff and actual provider evidence when needed.
3. **Explicit evidence attestation:** construct a short **ephemeral** JSON snapshot from those actual observations. The script does **not** fetch GitHub data, independently verify that supplied URLs are true or discover PR relations. A caller may not assert `inventory_complete: true` without examining the relevant live PR set. Likewise, `accepted_commit` requires independent default-branch acceptance of the **claimed outcome**, not any arbitrary merged SHA.
4. **Offline deterministic verdict:** run the script below. Any omitted field, missing/unknown relation, stale target SHA, incomplete inventory or unverified owner/writer status is **not READY**. An unrelated PR is not a global blocker. A task's `scope: forbidden` is UNSAFE even when other facts look attractive.
5. **Owner-controlled next step:** the output is advice, **not** a dispatch command. Before an actual agent invocation, re-fetch exact live HEAD, relevant PRs and writer state, and obtain the existing owning-domain approval. Never auto-close an Issue, update a roadmap, merge a PR, publish, buy credits, edit Control Plane telemetry or switch on a worker because the classifier printed `READY`.

**Cursor Pilot 06 review follow-up (2026-10-23):** one read-only Cloud Agent reviewed PR #112 at immutable head `59d1a6cd805596a21598e642321f005695cc668f` and independently ran **37/37 Python stdlib tests** ([Issue #115](https://github.com/DaniilSydorenko/.github/issues/115)). The review found a narrow fail-closed bug: simultaneous `accepted_commit` and `superseded_by` assertions previously selected `ALREADY_ACCEPTED` by precedence. The proposed same-branch correction now rejects both claims together with `NEEDS_EVIDENCE`. Both acceptance and supersession references must have the **same-repo GitHub `/pull/<number>` or immutable `/commit/<40hex>` URL shape**; generic `tree/main` and arbitrary GitHub pages are rejected. This validates URL syntax, **not** actual owner authority or commit ancestry. Five new negative/positive regression methods were added. Current total is **42 synthetic test methods (27 + 15)**; the earlier 37/37 Cloud proof belongs to the **reviewed old SHA**, not this amended HEAD. Rerun tests against the updated exact HEAD before merge, and never claim that a green older check covered these fixes.

## Verdicts and next actions

| Verdict | Meaning | Safe action |
| --- | --- | --- |
| `ALREADY_ACCEPTED` | **Exact same outcome** independently accepted at a verified immutable SHA | Reconcile existing owner Issue via its authorized workflow; no repeat coding |
| `SUPERSEDED` | **Owner changed the target**; original issue replaced by an evidenced, accepted implementation | Link approved replacement and update/close old Issue **only through owner workflow**; do not implement obsolete target |
| `EXISTING_PR` | Open PR already attempts this outcome | Review/continue **that PR**, request owner integration decision; no second writer |
| `WAITING_DEPENDENCY` | Pending dependency, active writer, overlapping paths or stacked base | Link precise blocker in owner Issue, work on another **independently authorized** task if available |
| `OWNER_GATE` | Human-only decision, domain scope or explicit dispatch permission not satisfied | Ask for specific owner choice once, then stop |
| `EXTERNAL_BLOCKED` | Missing real runtime/provider/environment evidence | Record exact fingerprint, wait for new evidence; avoid blind retries |
| `NEEDS_EVIDENCE` | Missing/stale/inconsistent observation; unknown does not mean false | Narrow fresh readback; do not invoke agent |
| `UNSAFE` | Clearly forbidden learner-owned/secret/destructive/out-of-scope operation | STOP; report without workaround |
| `READY` | Bounded, evidenced, permitted **candidate** task with no observed collision | Separate manual owner-approved invocation only, fresh preflight immediately before launch |

**Not-stuck rule:** A blocked decision is an **outcome**, not a reason to re-run the same prompt every hour. Specify the missing evidence, responsible owner and next *external event* that would justify rechecking. Continue only on unrelated owner-approved work. Two identical uninformative retries → BLOCKED under Low-Burn v2. `NO_READY_WORK` for a domain is a valid orchestration conclusion; the script classifies **one task at a time** and does not claim to find an eligible task globally.

## Observation reconciliation — experimental second layer (2026-10-23)

`evidence_reconcile.py` is the **offline consistency check** between a task's asserted evidence and a **separately captured** GitHub metadata observation. The snapshot envelope has two top-level keys: `task` (the existing `decision_gate.py` shape) and `observed` (readbacks from the authorized **owning** Issue and only its **relevant** PRs; never an unconditional seven-repo sweep).

Required `observed` fields:

- `repo` must match `task.repository`, `issue_number` must match the exact `task.issue` URL, `issue_state` must equal the issue-state assertion.
- `default_sha` must match both task `default_sha` and `checked_sha` at that observation. If the branch advances afterward, the entire check must be repeated.
- `related_inventory_complete: true` is a **reviewer-attested factual claim**, never guessed from a truncated search page. `related_prs` contains every PR the reviewer determined relevant, with `number`, exact `head_sha`, and `state: open|closed`. Every relevant PR must be classified in the task: missing, merged/closed or changed HEAD ⇒ `NEEDS_EVIDENCE`.
- `accepted_shas` lists only independently established **accepted default-branch implementation/replacement SHA proofs** (not unmerged PR heads). A claimed `ALREADY_ACCEPTED` or `SUPERSEDED` commit absent from this list is rejected. Merely adding an arbitrary SHA to both JSON copies is **not proof**.

These structural cross-checks reduce accidental **time-of-check/time-of-use** errors, but **do not** prove snapshot origin, atomicity, current time, correct semantic issue↔PR matching, owner authorization, absence of another writer or successful deployed acceptance. Both JSON objects could be fabricated; treat the result's `verification: CONSISTENT_ONLY` literally. `READY` is still a **candidate suggestion**, never an instruction to run an agent. Do not wire either CLI's exit code to `@cursor`, merge, publish, or a scheduled worker.

No new token/service cost, network access, storage, auth or GitHub mutations are introduced. The original `decision_gate.py` CLI is a **baseline-only advisory** without independent observation checks; prefer the reconciler for experiments with source-backed data. Follow the domain's explicit permissions and Low-Burn budget rules.

**Test evidence:** new `test_evidence_reconcile.py` has **15/15 local Python standard-library unittest passes** for stale `main`, changed/closed PR, changed Issue, incomplete/duplicated inventory, accepted-commit mismatch, supersession mismatch and safe `EXISTING_PR`. The initial 22 decision-gate synthetic methods remain unchanged. These results are **offline tests, not live GitHub API proof or CI**.

## Local verification (zero model tokens / network / side effects)

From `docs/initiatives/ai-engineering/`:

~~~sh
python3 -m unittest discover -v -p 'test_*.py'
python3 evidence_reconcile.py /path/to/temporary-observed-task-envelope.json
~~~

Exit code `0`: advisory `READY` only. Exit code `1`: valid non-ready decision. Exit code `2`: invocation/input file error. **Never use exit code 0 as permission to call `@cursor` or merge.**

One example **entirely synthetic**, not a claim about any live GitHub repository:

~~~json
{
  "schema_version": 1,
  "repository": "example/test",
  "issue": "https://github.com/example/test/issues/42",
  "evidence": {
    "default_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "checked_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "inventory_complete": true,
    "issue_state": "open",
    "accepted_commit": null,
    "accepted_proof": null,
    "related_prs": [
      {
        "number": 17,
        "head_sha": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "relation": "same_outcome"
      }
    ],
    "dependencies": [],
    "writer": "idle",
    "scope": "allowed",
    "owner_permission": "granted",
    "owner_gate": false,
    "external": "clear"
  }
}
~~~

Expected result: `EXISTING_PR`, **no new Cursor agent**. To test a truly unrelated open PR, change only the relation to `unrelated`; the result becomes `READY` *under the synthetic assumption that all supplied evidence and owner permission were correctly verified*.

## Synthetic regression matrix

`test_decision_gate.py` covers 27 test methods inspired by observed patterns, without private metadata or real repository mutation:

- Haversine: an **identically specified implemented outcome** is `ALREADY_ACCEPTED` only with checked accepted proof; an owner-approved **2.0.0 → 2.0.1** scope change is `SUPERSEDED` with separately verified accepted replacement; a closed Issue alone ≠ done.
- Ladvero: existing same-outcome PR and overlapping Gemini files stop duplicate execution; each green individual PR is **not** a sequential merge proof.
- Handbook: stacked base routes to dependency resolution, not re-authoring accepted/drafted chapters.
- Career Intelligence: production DATA approval remains an `OWNER_GATE`.
- Labs: learner-owned task is `UNSAFE` for the agent; a separate, authorized bounded engineering leaf may be `READY`.
- Incomplete PR scan, old default SHA, unknown writer, unverified dependency, missing proof and malformed PR evidence all fail closed.
- An unrelated PR does **not** block all work.

**Optional supersession evidence field:** `"superseded_by": {"accepted_sha": "<40-character accepted replacement commit>", "ref": "https://github.com/<owner>/<repo>/pull/<number>", "reason": "owner changed scope from X to Y"}`. An explicit source-backed owner decision is mandatory: the classifier checks this field's *shape*, not the legal or technical accuracy of the supplied claim. A mismatched version without approved replacement is `NEEDS_EVIDENCE`, **never** permission to auto-close an issue.

**Test evidence:** source and tests were run locally with Python 3 standard-library `unittest`, **22/22 previously passed before Pilot 06 correction**. This is code-level simulation, **not** proof of live GitHub ingestion, semantic LLM accuracy, atomic branch locks, task auto-selection, real provider costs or a safe always-on dispatcher. Applicable GitHub PR-head CI remains independently UNKNOWN until actually observed.

## Exit criteria before even considering real dispatch integration

- Domain owner selects a bounded, public-safe **read-only** case and verifies snapshot data independently from GitHub; output matches evidence, including existing work or missing proof.
- At least one stale Issue, one active same-outcome PR, one dependency chain, one owner gate and one genuinely eligible leaf are tested against **fresh actual provider data**, with discrepancies recorded in the *owning* Issue/PR (not a central status tracker).
- Explicitly verify that unknown fields cannot be manufactured as `READY` by a wrapper; source provenance validation, issue/PR correlation and concurrency remain **outside this script**. Any mismatch fails closed.
- Do not couple to `@cursor`, API calls, branch locking, workflows or central GRS without measured value, specific domain authority and a separately reviewed owner decision.
- The same experiment may be simplified or deleted if a provider-native, evidence-safe approach proves better. **No universal seven-repo enforcement** (GitHub HQ Option B remains binding).
