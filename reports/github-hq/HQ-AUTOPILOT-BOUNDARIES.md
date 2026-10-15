# [CAREER][GITHUB] — HQ / Autopilot Operating Boundaries

Date: 2026-10-11
Status: ACTIVE

## One program, two control views

There is one GitHub program, but there are two intentionally separate roadmaps:

- `reports/github-hq/ROADMAP-LIVE.md` — owned by the synchronous [CAREER][GITHUB] HQ chat.
- `reports/github-autopilot/ROADMAP-2026-10-11.md` — owned by GitHub Autopilot.

Neither worker edits the other's roadmap.

The HQ roadmap is the owner-facing source for full-program status, percentages, newly discovered gaps, owner gates and cross-repository coordination.

The Autopilot roadmap is the execution worker's own operating plan.

## [CAREER][GITHUB] HQ owns

- owner-facing roadmap and milestone status;
- cross-repository strategy and sequencing;
- public/private architecture and publication readiness;
- owner-decision gates;
- repository metadata/profile/pins/topics planning;
- central governance policy;
- safety review of risky merges;
- exact-head verification before synchronous merges;
- triage of new gaps/bugs into the HQ roadmap;
- coordination when repository/domain ownership is ambiguous.

## GitHub Autopilot owns

- bounded scheduled maintenance;
- bounded governance hardening;
- bounded repository-health fixes;
- drift detection;
- preparation of safe PRs inside its allowed surfaces;
- CI/retry diagnostics that do not require owner decisions;
- roadmap execution inside its own operating plan.

## Domain workers own

- Engineering Labs product/training implementation;
- Engineering Handbook authored theory/content;
- Career Intelligence product/data/platform implementation;
- Ladvero product implementation;
- Haversine domain/API evolution when it exceeds repository maintenance/release engineering.

GitHub HQ may audit these repositories for readiness and may perform explicitly authorized maintenance/release-engineering work, but must not silently take over domain ownership.

## Scope of HQ completion — domain application PRs are not HQ deliverables

Owner clarified on 2026-10-13: the GitHub HQ and GRS roadmap **must not require completion of every pull request in other applications**. This is scope ownership, not permission to close/delete those PRs, rewrite their roadmaps or weaken any safety gate.

- **HQ owns:** its `.github` governance/profile work; GitHub-side evidence/discovery, safe CI/GRS verification, read-only cross-repository conformance, and owner-gated public visibility decisions.
- **Domain owners own:** their own product code, content, dependencies, refactors, acceptance, PR merges, releases, and local roadmaps in ListingKit/Ladvero, Career Intelligence, Engineering Handbook, Engineering Labs and Haversine. Domain PR/Draft counts are observations only.
- **M4 distinction:** HQ may document exposure, audit current tree/history readiness, and ask for publication decisions. Domain teams own code/data extraction. An unfinished domain extraction is a *specific publication prerequisite* if the owner wishes to make that repo public, **not** a reason to block unrelated GitHub/Governance milestones. Do not mark the publication gate done while risks remain.
- **GOV-M07/M08 distinction:** existing seven-repo governance discovery/operational evidence may be required under the agreed scope; clearing domain PR queues, finishing Handbook chapters, shipping product features and updating every dependency are **not** required. C01–C07 enforcement still requires separate owner decision #56.
- **Finish First applies within ownership.** Review and close GitHub-owned PRs before opening more GitHub governance work; don't absorb domain PR stacks into HQ simply because they are large. Keep their status truthful, never inflate milestone percentages or silently amend existing acceptance criteria.

## Infrastructure Reset v1 — owner-approved operational focus (2026-10-15)

The primary HQ deliverable is reliable, low-friction GitHub infrastructure across seven independently owned repositories. **Infrastructure readiness does not depend on domain product features, content completion, open PR backlog size or coordinated releases.** A domain's PR queue is evidence for collision checks when relevant to a concrete HQ write, not an HQ completion queue.

The existing GRS, per-repo local CI, registry and Control Plane are the platform; do **not** introduce a new scheduler, dashboard, database, duplicate tracker, agent framework, or standing human review for ordinary authorized changes. Reuse established bounded Class A/B permissions **only for the worker that owns them**; do not transfer merge authority to synchronous HQ. Keep Class C/security, credential, visibility, release, destructive-history and owner-publication gates unchanged.

Apply the 12-stage engineering round internally as a coherent work cycle, **not** twelve manual owner approvals or one PR per stage. If a single security-sensitive PR needs independent approval, record that one gate and continue independent HQ work rather than repeatedly modifying it without a real defect. No new C01–C07 binding enforcement without owner issue #56 approval. No change to M4's existing scope or acceptance gates without separate explicit owner approval.

The live HQ roadmap should stay at **150 lines / 15 KiB maximum**; preserve its detailed pre-reset content through immutable Git history rather than copy outdated snapshots into active status. Updating the canonical score still requires evidence and its original milestone exit gate, not cleaner presentation alone.

## Collision rules

Before every mutation:

1. inspect current default branch;
2. inspect open PRs;
3. inspect the exact target branch/head;
4. inspect current CI;
5. inspect whether another worker already changed the same surface;
6. stop, rebase, or choose a different task if ownership or file overlap is unclear.

Never merge an exact head that has changed since verification.

Never force-update a branch without an expected SHA lease.

Never change repository visibility without explicit owner approval.

Never treat a scheduled worker failure as permission to take over its entire domain.

## Roadmap synchronization rule

HQ and Autopilot may report different percentages because they measure different views.

They must agree on factual repository state.

When the HQ discovers a real bug, gap or required task:

- add it to the HQ roadmap as `[NEW]`;
- do not silently expand an old task;
- do not write it into the Autopilot roadmap unless Autopilot itself adopts it.

When Autopilot completes work that changes program state, HQ updates its own roadmap on the next synchronous round after live verification.

## Finish-first closeout contract (HQ execution, not new fleet enforcement)

This is a **completion protocol**, not a new roadmap, task store, scheduler, governance authority, or mandatory C01–C07 adoption rule. It uses the already-approved seven-repository scope and the existing authority/CI controls.

1. **Close before creating.** At the start of an HQ engineering round, first inspect still-open, non-superseded PRs and unfinished milestone exit gates. Prefer accepting or unblocking the highest-value existing change over starting another PR. A new PR requires an independent missing implementation or real defect, not a desire for cleaner reporting. Do not disturb another domain's stacked PR or Dependabot maintenance lane.
2. **One work product at a time.** In each owned work lane, finish the currently selected deliverable to `MERGED + remote default-branch verification`, or to a clearly documented `BLOCKED / OWNER DECISION`, before starting an unrelated deliverable. A GREEN test, Draft, review-ready label or updated roadmap is *not* completion. Release/deployment/runtime gates remain separate when required by the domain.
3. **Standing vs current-run authorization.** Control Plane `AUTHORITY.md` already contains **standing owner authorization** for a worker's **own** bounded Class A/B PR. That authorization may satisfy the central policy's `current-run-explicit-authorization` requirement **only after** the same worker, on the current run, verifies actual owner/domain scope, classification, non-Draft status, fresh mergeability, unchanged exact HEAD, required CI/security, open reviews, no overlapping worker, and no owner gate. It grants **nothing** to synchronous HQ, owner-authored PRs, Class C, third-party/domain PRs, publication, visibility, history rewrite, credentials, stable releases or security/evidence semantics. In ambiguous cases, STOP; do not invent authority.
4. **Finite blocker treatment.** One fresh diagnosis and the existing bounded retry budget per material connector fingerprint. Two equivalent failures with no new evidence mean no third identical attempt or another generic report; record the exact blocker and its responsible authority **once**, then switch to a non-colliding useful lane. An owner-only decision is a discrete pending input, not proof that unrelated engineering is blocked.
5. **One owner decision batch.** Group genuinely owner-only remaining decisions with the smallest concrete choice, affected refs, risks and exact actions. Do not repeatedly request per-PR permission where a valid standing Class A/B approval already applies; conversely do not bundle a security-sensitive change into a safe-merge authorization.
6. **Fixed definition of done.** Milestone `100%` requires every **existing** acceptance gate for its approved scope, accepted default-branch evidence, and operational or release proof where its original contract requires it. A documented owner deferral may narrow *future scope only with explicit approval*; it never silently converts unfinished work to DONE. Historical percentages are labeled estimates; accepted/closed milestone counts have fixed denominators and are never inflated by PR/commit volume.
7. **Stop when finished.** On verified in-scope acceptance, mark that unit complete and retire its execution queue; do not manufacture follow-up governance work. Branch cleanup is a post-merge hygiene task with separate dependency/ref/recovery safety, not a release prerequisite unless it demonstrably affects correctness/security.

**Finish-first outcome per round:** `ACCEPTED` (default-branch SHA), `OWNER_DECISION` (precise input), `EXTERNAL_BLOCKED` (problem fingerprint and next event), or `CONTINUE_ELSEWHERE` (independent safe task). Record it in existing PR/Issue and canonical roadmap only; **no new status database**. Evidence of a repeated blocker can justify a specific regression fix, but not an unbounded new Governance v2.

## Finish-line rule

Do not create work merely to keep activity going.

A task may be added only when it is required by an existing milestone goal, a discovered safety/correctness defect, or an explicit owner request.

This prevents an endless-roadmap failure mode.
