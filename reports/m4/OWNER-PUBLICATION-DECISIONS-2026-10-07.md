# M4 — Owner publication decisions

Date: 2026-10-07
Status: **PREPARED — decisions not yet granted**

This packet narrows M4 to the owner choices that cannot be made safely by automation.

## Recommended defaults

### Engineering Labs

Current repo shape is strongly aligned with a future full-repository public release:

- README explicitly describes the platform as public-safe;
- exercises are synthetic;
- the canonical Mission → Stage → Scenario → Task model is documented;
- employer attribution boundaries are already explicit;
- the repository contains implementation, architecture, tests and learning-system evidence that are useful to a hiring audience.

**Recommended default:** keep the repository private while Engineering Labs is still proving its product/learning loop. The preferred eventual publication model remains the **full repository**, but GitHub readiness alone is not sufficient.

Before the publication decision is requested, the Labs-owning product lane should prove at least one real end-to-end training loop:

- Platform Core is usable for a real Mission;
- the canonical Mission → Stage → Scenario → Task model works in practice;
- one canonical Mission reaches BUILD → HARDEN → EVOLVE where appropriate;
- Daniil dogfoods the Mission by performing the learning work himself;
- the dogfooding cycle produces reviewable practice artifacts and concrete platform feedback.

Only after that product proof should the GitHub release gates (license, GRS consumer, quality/build, secret scan, metadata) become the final publication checklist.

Owner decision:

- [ ] APPROVE full-repository public release after product proof **and** GitHub release gates are green
- [ ] KEEP private longer while product/dogfooding matures
- [ ] REQUIRE sanitized projection instead

No option is selected by automation.

### Engineering Handbook

The repository contains both public-suitable theory and a personalized `daniil/` surface.

The theory/experiment content is a strong public knowledge artifact, but the personalized area must be audited before full-repository publication.

**Recommended default:** do **not** flip the full repository public yet. First perform a public-safety audit of `daniil/`, `automation/`, operating-system docs and generated release artifacts. If no private career evidence or internal planning detail remains, full-repo publication can become the preferred option; otherwise publish a sanitized projection.

Owner decision:

- [ ] APPROVE full-repository publication after private-surface audit
- [ ] APPROVE sanitized/public projection only
- [ ] KEEP private

No option is selected by automation.

### Career Intelligence

The repository is the canonical engineering source for a system whose README explicitly separates public projection from a private career ledger. The repo contains data-ingress, canonicalization, API, database and automation surfaces that may reveal more of the private data model and provenance than the public website should expose.

**Recommended default:** **KEEP the canonical repository private for now.**

Treat the public website/API projection as the public artifact. Revisit source publication only after a dedicated clean-room/public-source design proves that private ledger semantics, source records, provenance, compensation, recruiter/interview material and private company data cannot leak.

Owner decision:

- [ ] KEEP canonical repository private; public website/API is the public artifact
- [ ] DESIGN separate sanitized public-source repository/artifact
- [ ] CONSIDER full-repository publication only after dedicated data-boundary audit

Automation must default to the first option operationally until the owner explicitly chooses otherwise.

## Decision hierarchy

For all three repositories:

1. **public safety beats portfolio completeness**;
2. **truth beats visual polish**;
3. **owner approval beats automation convenience**;
4. **full-repo publication is preferred only when the private/public boundary is naturally clean**;
5. **sanitized projection is preferred when canonical truth contains private material**.

## What automation may do before owner decisions

Automation may:

- audit public-safety surfaces read-only;
- prepare GRS consumer manifests through the owning lane;
- prepare licensing recommendations;
- prepare README/metadata recommendations;
- run secret/data exposure checks;
- create central evidence and decision packets;
- verify CI/build/test status;
- identify exact blockers.

Automation may not:

- change repository visibility;
- delete private material to force public readiness;
- rewrite canonical career truth for public convenience;
- expose employer/private data;
- mark an owner option as approved.

## Current M4 blocking decisions

Only these decisions are genuinely owner-gated:

1. Engineering Labs publication timing **after** Platform Core + first real Mission/dogfooding proof and GitHub release gates are green.
2. Engineering Handbook full-repo vs sanitized projection.
3. Career Intelligence canonical repo vs public artifact strategy.

Everything else should be prepared by the relevant automation/owner lanes before asking Daniil to decide.
