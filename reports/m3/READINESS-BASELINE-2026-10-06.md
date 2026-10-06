# M3 — Public Flagship Wave 1 readiness baseline

Date: 2026-10-06
Status: **ACTIVE — private candidates remain visibility-gated**

## Purpose

Establish a measured GitHub-facing readiness baseline for M3 without changing repository visibility or redefining domain architecture.

## Candidate classification

| Repository | GRS class | Current visibility | Portfolio intent | Measured GitHub baseline |
| --- | --- | --- | --- | --- |
| engineering-labs | engineering-labs | private | flagship / pin candidate | README, .gitignore and secret-scan workflow present; license, SECURITY.md, CONTRIBUTING.md, PR template and repository manifest not found |
| engineering-handbook | knowledge | private | flagship / pin candidate | README, .gitignore and secret-scan workflow present; license, SECURITY.md, CONTRIBUTING.md, PR template and repository manifest not found |
| career-intelligence | platform | private | flagship / pin candidate | README, .gitignore and secret-scan workflow present; license, SECURITY.md, CONTRIBUTING.md, PR template and repository manifest not found |
| haversine-geolocation | oss-library | public | flagship / pin candidate | GRS consumer PR #33 active; measured missing SECURITY.md, CONTRIBUTING.md and issue taxonomy remain truthful FAILs until remediated |
| listing-kit / Ladvero | product | private | future flagship | write ownership belongs to Ladvero Autopilot; central GitHub Autopilot remains read/audit only |

## Changes made in this pass

Central pilot manifests were added for engineering-labs, engineering-handbook and career-intelligence. These record intended GRS class, current private visibility and portfolio intent without changing any consumer repository or public/private boundary.

## Public-readiness rule

A private M3 candidate may be prepared while private, but visibility is always an owner gate. GitHub Autopilot must not make a repository public. Before recommending public release, require at minimum:

1. canonical domain architecture/status is current;
2. public README clearly states purpose and status;
3. no secrets/private/company/personal ledger data;
4. licensing decision is explicit;
5. relevant tests/CI and secret hygiene are green;
6. GRS consumer produces measured results;
7. public projection does not expose private canonical data;
8. owner approves visibility change.

## Priority

1. Continue Haversine GRS audit/remediation when connector write path permits.
2. Prepare engineering-labs as the first private flagship readiness candidate because its Mission → Stage → Scenario → Task model is already canonical in the CAREER ecosystem.
3. Prepare engineering-handbook next as the public theory/knowledge companion.
4. Keep career-intelligence most conservative because its public engineering projection must remain separated from private career facts/evidence/provenance.
5. Keep Ladvero under its separate writer Autopilot and public-safety gate.

## Decision

M3 is not a mass-publication milestone. It is a controlled flagship-readiness wave. Current private candidates remain private until their domain owners and public-safety gates are satisfied.
