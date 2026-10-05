# GitHub Repository Standard (GRS) v1

Status: **Draft / canonical bootstrap**
Canonical home: `DaniilSydorenko/.github`

GRS is the policy-as-code contract for repositories in the DaniilSydorenko GitHub portfolio. Repository quality must be explicit, class-aware, versioned, auditable, and enforceable where GitHub capabilities allow.

## 1. Authority model

GRS defines repository governance. It does not define product architecture or career truth.

- Career Intelligence owns career facts, evidence, provenance, gaps, and priorities.
- Project repositories own their implementation and project-specific architecture.
- GRS owns repository-quality policy, repository classes, machine-readable contracts, validation, and GitHub governance expectations.
- Human-controlled gates remain authoritative for private → public visibility, external credentials, destructive administration, and consequential releases.

## 2. Requirement levels

| Level | Meaning | Validator behavior |
| --- | --- | --- |
| REQUIRED | The repository must satisfy the rule for its class. | FAIL |
| RECOMMENDED | Strong default; omission needs no hard block. | WARN |
| OPTIONAL | Supported but not expected. | PASS / informational |
| N/A | Deliberately not applicable. | Ignored |

A numeric health score may be displayed later, but `PASS / WARN / FAIL / N/A` is authoritative.

## 3. Repository classes

GRS v1 defines seven classes:

- `profile` — special public GitHub profile repository.
- `oss-library` — reusable public library/package intended for external consumers.
- `product` — application/product repository.
- `engineering-labs` — deliberate-practice repository built around engineering missions/scenarios/tasks.
- `knowledge` — handbook/documentation/knowledge-system repository.
- `platform` — data, automation, orchestration, or control-plane repository.
- `historical` — frozen historical evidence; safe and honest, but not forced to imitate a modern active project.

## 4. Governed surfaces

Every class profile must explicitly classify repository identity, collaboration, engineering verification, security/supply chain, architecture/decisions, releases, and GitHub governance controls as REQUIRED, RECOMMENDED, OPTIONAL, or N/A.

Security baseline includes secret scanning, minimal GitHub Actions permissions, immutable action pinning where practical, and no committed secrets, private data, company-confidential data, credentials, private keys, databases, or backups.

## 5. Per-repository manifest

Managed repositories declare their contract in `.github/repository.yml`.

```yaml
schema: 1
standard:
  version: 1
repository:
  class: oss-library
  maturity: maintained
  visibility: public
portfolio:
  flagship: true
  pin_candidate: true
```

Overrides must be explicit, narrow, and justified. A repository may not override critical security requirements merely to make validation green.

## 6. Enforcement architecture

```text
GRS policy + class profile + repository manifest
                    ↓
             repository validator
                    ↓
          PASS / WARN / FAIL / N/A
                    ↓
        reusable GitHub Actions check
                    ↓
 required status check / ruleset where supported
```

Critical deterministic checks should block merge where GitHub plan/capabilities permit. Recommended rules warn rather than creating bureaucracy.

## 7. Versioning

GRS is versioned. Repositories declare the standard version they implement. A future upgrade must produce migration requirements rather than silently breaking every repository.

## 8. Historical/frozen contract

Historical repositories preserve engineering history. They must remain safe, understandable, and non-misleading, but are not modernized merely to satisfy contemporary cosmetics.

Historical baseline:
- README/status clearly communicates historical/frozen state.
- no live secrets/private data.
- existing licensing remains clear.
- no misleading claim of active maintenance.
- no unnecessary feature development.
- security remediation remains allowed.

## 9. Rollout

1. Freeze GRS v1 specification.
2. Establish this repository as canonical control plane.
3. Add machine-readable schema and class profiles.
4. Implement repository validator.
5. Implement reusable governance workflow.
6. Add community-health defaults/templates.
7. Pilot on profile repository and Haversine.
8. Roll out to active repositories.
9. Apply reduced historical/frozen contract.
10. Add scheduled drift detection and remediation proposals.
11. Integrate verified governance/evidence signals with Career Ecosystem.
12. Evolve toward GitHub Autopilot.

## 10. Safety gates

GRS automation must not change repository visibility, rotate/revoke credentials, perform destructive repository administration, or bypass human-controlled security/release gates.

A historically exposed Google Maps API key remains a deferred explicit verification/revocation item before the relevant final archive/public-release gate.
