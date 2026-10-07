# GRS rollout preflight — Engineering Labs

Date: 2026-10-07
Status: central readiness evidence only; consumer repository remains owner-controlled and private

## Canonical pilot

Central manifest: `grs/pilots/engineering-labs.repository.json`.

Expected identity: schema 1; standard v1; class `engineering-labs`; maturity `active`; visibility `private`; flagship and pin candidate both true.

## Live read-only evidence

Observed on the Engineering Labs default branch:

| Surface | Result | Evidence |
| --- | --- | --- |
| README/status | PASS | README explicitly describes Engineering Labs as public-safe and defines synthetic-only MVP boundaries. |
| .gitignore | PASS | Present in established baseline. |
| secret hygiene workflow | PASS | `.github/workflows/secret-scan.yml` present. |
| licensing decision | FAIL | `LICENSE`, `LICENSE.md`, `LICENSE.txt` not found. |
| PR template | FAIL | `.github/PULL_REQUEST_TEMPLATE.md` not found. |
| issue taxonomy | FAIL | `.github/ISSUE_TEMPLATE` not found. |
| SECURITY.md | WARN | Not found. |
| CONTRIBUTING.md | WARN | Not found. |

Expected deterministic GRS result for class `engineering-labs`: **3 FAIL, 2 WARN**.

## Ownership and publication boundary

This worker records but does not remediate consumer-repository gaps. Engineering Labs has a separate Career Ecosystem writer. No visibility change is authorized here.

The README is positive publication evidence, not publication approval. It explicitly excludes authentication, databases, production backends, real network attacks, live model calls, external telemetry vendors, uploads, real WebSocket servers and external network requests for lab simulations.

## Central completion criterion

The central control plane validates the pilot manifest deterministically, including class, private visibility, maturity and flagship/pin intent. Consumer FAIL/WARN findings remain truthful until the owning worker changes the measured surfaces.
