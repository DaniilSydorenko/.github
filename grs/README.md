# GitHub Repository Standard (GRS)

This directory is the canonical home of GRS policy-as-code for the DaniilSydorenko GitHub portfolio.

## Core model

```text
GRS policy
  → repository class
    → per-repository manifest
      → validator
        → reusable GitHub workflows
          → PASS / WARN / FAIL / N/A
            → required checks / rulesets where supported
```

## Requirement levels

- **REQUIRED** — absence or violation fails governance validation.
- **RECOMMENDED** — absence or violation emits a warning.
- **OPTIONAL** — supported but not expected.
- **N/A** — deliberately not applicable.

A numeric health score may be derived for presentation, but it must never hide a failed REQUIRED control.

## Repository classes

GRS v1 defines: `profile`, `oss-library`, `product`, `engineering-labs`, `knowledge`, `platform`, and `historical`.

## Governed surfaces

Class profiles explicitly decide applicability and level for identity/status, licensing, generated-artifact hygiene, security, collaboration templates, engineering checks, dependency/supply-chain hygiene, Actions safety, branch governance, releases/provenance, architecture/ADRs, metadata, public readiness, and historical/frozen behavior.

## Per-repository manifest

Managed repositories carry `.github/repository.json`, validated against the canonical GRS schema. JSON is the canonical GRS v1 serialization so validation remains dependency-free and deterministic across repositories.

Repository-specific overrides must be explicit, schema-valid and limited to controls GRS marks overridable. An override must never silently weaken a non-overridable security control.

## Enforcement

- REQUIRED violation → `FAIL`
- RECOMMENDED violation → `WARN`
- satisfied control → `PASS`
- non-applicable control → `N/A`

Human-controlled gates remain mandatory for consequential operations including private → public visibility changes, credential revocation/rotation, destructive administration, and sensitive releases.

## Rollout order

Specification → schema/class profiles → validator → reusable workflow → community defaults → pilots → active repositories → historical contract → drift detection → Career Ecosystem/Autopilot integration.
