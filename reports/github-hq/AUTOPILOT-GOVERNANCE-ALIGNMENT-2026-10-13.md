# Autopilot Governance Alignment — bounded audit, 2026-10-13

**Mode:** observed configuration + policy files + latest telemetry; no scheduler mutation, no new worker, no merge. Existing GOV-M07/M08 and AUTO-GOV-02/04/06/07 own remediation. C01–C07 issue #56 remains unapproved.

## Evidence inspected

Live scheduler configuration via task inspection: five enabled workers (Control Plane Manager hourly; GitHub hourly; Ladvero hourly; Career Ecosystem hourly; Norway Scan weekly), plus one **disabled historical Career Ecosystem task** (do not mistake for second active worker). Last-run timestamps observed on 2026-10-13 for four hourly workers and 2026-10-12 for Norway. Scheduler prompts were read, but **runtime trace of policy-file loading is not available**.

GitHub files inspected at current default branch: `.github/governance/autopilot-merge-policy.json`, `autopilot-control-plane/{AUTHORITY.md,CONTROL_PLANE.md}`, `listing-kit/.autopilot/worker-policy.md`, `career-intelligence/.autopilot/worker-policy.md`, `autopilot-control-plane/policies/norway-target-companies-scan.md`, and four worker telemetry v2 files. Sources are mutable; verify SHA again before changes.

## Clause ownership and duplication matrix

| Rule | Canonical owner | Local tightening / summary | Classification | Minimal action |
| --- | --- | --- | --- | --- |
| Cross-repository engineering GRS / C01–C07 | `.github/governance`, owner gate #56 | Control Plane references compatibility | Conflicting authority wording in ListingKit and Career worker policies | LINK to `.github` global engineering; retain Control Plane execution governance |
| Fleet/scheduler observation, retry budget, cooldown, telemetry v2 | `autopilot-control-plane/CONTROL_PLANE.md` + dedicated protocols | Scheduled bootstrap operational specifics | Valid local specialization; some harmless repeated text | KEEP local execution instructions; link canonical protocol |
| Actor authorization and Class A/B scope | `autopilot-control-plane/AUTHORITY.md` + worker/repo narrowing | Local worker policies, bootstrap | **Potential semantic conflict** with `.github/governance/autopilot-merge-policy.json` `current-run-explicit-authorization` | INVESTIGATE and define conjunctive proof; no expanded merge rights |
| Exact-head CI, non-draft, no collision, owner/security gates | `.github/governance/autopilot-merge-policy.json` + actual repo CI | Control Plane AUTHORITY.md and local policies | Valid local tightening, normative duplication | KEEP local quick instructions, link source |
| Domain content, release and security restrictions | Domain repo `AGENTS.md` / worker policy / release rules | Central forbidden operations | Valid local specialization | KEEP; deny cross-domain writes |
| Scheduler prompt | Scheduler live configuration | Bootstrap-only durable contract | Valid specialization, not a canonical policy store | KEEP; require current-policy discovery proof |
| Norway hiring access / no contact | Control Plane `policies/norway-target-companies-scan.md` | Weekly bootstrap specifics | Valid local specialization | KEEP |
| Old disabled Career Ecosystem task | Scheduler historical record | Prior bootstrap includes stale hardcoded PR #16 SHA | Historical artifact, **not active duplicate worker** | KEEP disabled; no scheduler mutation |

## Worker-by-worker proof and UNKNOWNs

| Worker | Live schedule observed | Bootstrap policy references | Latest telemetry (not current health proof) | Runtime policy SHA loaded? |
| --- | --- | --- | --- | --- |
| Control Plane Manager | enabled hourly; last run 2026-10-13 11:00Z | Control Plane main; scheduler and GitHub live evidence | retirement-ready observation mode | **UNKNOWN** |
| GitHub Autopilot | enabled hourly; last run 2026-10-13 11:05Z | central main and local owning-lane evidence | DEGRADED CONNECTOR, observed 2026-10-13 08:57Z | **UNKNOWN** |
| Ladvero PR Autopilot | enabled hourly; last run 2026-10-13 10:17Z | Control Plane + ListingKit local worker policy | BLOCKED SECURITY, observed 2026-10-13 10:17Z; PR #194 history gate | **UNKNOWN** |
| Career Ecosystem Autopilot | enabled hourly; last run 2026-10-13 10:33Z | Control Plane + CI/Handbook/Labs current repo state | DEGRADED CONNECTOR, observed 2026-10-13 10:31Z | **UNKNOWN** |
| Norway Target Companies Scan | enabled weekly; last run 2026-10-12 06:08Z | explicitly names Control Plane policies including Norway-specific policy | WORKING, observed 2026-10-12 06:04Z | **UNKNOWN** |

**No actual policy-fetch/parse/version trace was obtained.** Prompts instruct reading files but are not proof. Do not report workers compliant on policy loading or policy-version pinning.

## Safe merge authorization interpretation — PROPOSED, not enforced

Treat standing Class A/B owner grant as *eligibility only*, never automatic merge permission. Each run must freshly demonstrate own-scope Class A/B authorization, local restrictions, no collisions, exact PR head and required checks, non-draft and current mergeability, no owner/security/release gates; otherwise STOP. `current-run-explicit-authorization` remains **unresolved terminology** until owner-approved reconciliation with central policy; no bypass by interpreting standing grant as unconditional. Tests should cover allowed eligible Class A/B; denied draft, changed head, red/missing CI, out-of-domain, owner gate, collision, unknown authorization, historical secret scan unresolved.

## Bounded implementation sequence

1. Domain-owned small wording/link PRs for ListingKit and Career worker policy. No scheduler changes.
2. HQ + Control Plane owners reconcile merge semantics and add deterministic allow/deny regression tests in existing validation surface, behind #56 for any new binding requirement.
3. Read-only worker policy-loading evidence probe (entrypoint/prompt, source path, SHA, missing-file behavior, local tightening). If execution environment cannot expose the trace, mark UNKNOWN; do not build a service.
4. Verify allowed/denied cases with deterministic tests and exact-head CI; preserve independent lanes while connector/security blockers persist.
5. Freeze when five authority questions and policy consumption evidence have reproducible answers. No new milestone, worker, dashboard, database, status store or schedule mutation.

**Owner decisions:** issue #56 for C01–C07 binding; interpretation of current-run authorization if semantics materially change; domain owner for local policy edits; security owner for ListingKit historical Gitleaks classification; any scheduler modification separately owner-gated.
