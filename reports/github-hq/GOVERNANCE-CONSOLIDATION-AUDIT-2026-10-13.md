# Governance Consolidation — Fleet Conformance Audit (2026-10-13)

Status: PROPOSED / READ-ONLY EVIDENCE. Owner: GitHub HQ. This is not a new mutable status store, and does not supersede GOV-M01–M08, repository-local roadmaps, or owner gate #56.

## Inventory scope

GitHub installation search returned 17 repositories: 8 active and 9 archived. The existing central governance discovery registry intentionally covers seven engineering repositories; the eighth active repository is the profile repository `DaniilSydorenko/DaniilSydorenko`. Archived repositories are inventory-only, not candidates for automatic governance mutation.

| Active repository | Default branch | Local workflows observed | Canonical GRS manifest `.github/repository.json` |
| --- | --- | ---: | --- |
| `.github` | main | 3 | absent |
| `autopilot-control-plane` | main | 6 | absent |
| `listing-kit` | main | 3 | absent |
| `career-intelligence` | main | 4 | absent |
| `engineering-handbook` | main | 3 | absent |
| `engineering-labs` | main | 3 | absent |
| `haversine-geolocation` | master | 11 | present |
| `DaniilSydorenko` (profile) | main | 3 | absent; outside seven-repo registry |

This is a path-presence and workflow-name inventory, not a full semantic workflow comparison. Missing exact-path files do not establish absence of equivalent controls. Local product/release CI is legitimate and must not be flattened.

## Confirmed central authorities

- `governance/ENGINEERING-GOVERNANCE-V1-DRAFT.md`: C01–C07; still DRAFT, pending owner gate #56.
- `governance/repository-registry.json`: seven-repository discovery index; points to local authority, does not duplicate mutable progress.
- `grs/OPERATING-MODEL.md`, `grs/repository.schema.json`, `grs/classes/profiles.json`, `grs/validator.py`, `grs/audit_repository.py`, `grs/check_policy_drift.py`: central deterministic governance policy and validation.
- `governance/autopilot-merge-policy.json`: default-deny merge conditions; no owner-gate bypass.
- `.github/workflows/grs-control-plane.yml`, `.github/workflows/reusable-autopilot-health.yml`: central validation and shared health implementation.

## Acceptance gaps (existing GOV-M07/M08, not new milestones)

| ID | Gap | Proposed acceptance |
| --- | --- | --- |
| GOV-CONS-01 | Policy-to-local implementation matrix incomplete | Compare each common contract with all seven repositories' actual files and workflow semantics; classify canonical/shared, legitimate local, duplicate, conflict, exception |
| GOV-CONS-02 | Six canonical GRS manifests absent | Owner-approved non-enforcing pilot or documented exemption for each; schema validation and exact-head CI |
| GOV-CONS-03 | Central standards not yet mandatory | Resolve C01–C07 owner gate #56 before imposing required cross-repo checks |
| GOV-CONS-04 | Cross-repo CI/security equivalence not proven | Inspect actual job definitions, permissions, pinning, history depth, secret scan execution and branch rules; no equivalence claims from filenames |
| GOV-CONS-05 | PR changed-file collisions observed | Preflight open PRs and touched files, serialize conflicting work; exact-head CI after integrations |
| GOV-CONS-06 | Branch lifecycle policy absent | Read-only paginated branch inventory, merged/open PR links, unmerged commit safety and protection checks, dry-run first; owner approval before deletion |
| GOV-CONS-07 | Profile repo outside seven-repo discovery | Explicitly classify profile as eighth governed or documented lightweight exception; do not silently expand enforcement |
| GOV-CONS-08 | Governance freeze acceptance incomplete | Reproducible fleet audit, owner approvals, stable engineering rounds, overhead review and no-silent-authority-expansion evidence |

## Branch lifecycle design (proposal only)

1. Enable native delete-head-branch-on-merge per repository only after confirming repo settings and owner decision.
2. A shared reusable **audit-only** workflow may be hosted centrally, called by small local wrappers; local workflow owns schedule and permissions.
3. No branch deletion by age alone. Exclude default, protected, open-PR, active worker/release and branches with unreviewed unmerged commits. Preserve audit artifacts.
4. Only after a dry-run acceptance may a separate explicitly authorized deletion mode be proposed. Never grant a central token blanket write access to all repositories.

## Execution order

1. GOV-M07: inventory semantic policy and workflow differences; document exact conflict/exception evidence.
2. GOV-M08: owner approval of C01–C07 and adoption boundaries.
3. GOV-M07: small local GRS manifest PRs with CI, without touching product roadmaps or workers.
4. GOV-M07: branch audit-only reusable workflow pilot; verify reports and zero deletes.
5. GOV-M08: fleet acceptance, three stable engineering rounds, freeze.

## Evidence limitations

The 17-repository list, seven manifest probes, workflow filenames and central contract contents were inspected live on 2026-10-13. This document does not assert all 17 branch histories, complete YAML semantics, branch protections, archived histories, runtime scheduler state or full historical scans were audited. Existing roadmap percentages remain unchanged pending accepted evidence.
