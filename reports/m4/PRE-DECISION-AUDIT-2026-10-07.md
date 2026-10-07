# M4 — Pre-decision public-safety audit

Date: 2026-10-07  
Status: **ACTIVE — automation-safe preparation advanced; owner publication decisions remain pending**

## Purpose

This audit converts the M4 publication-boundary policy into a live, repository-specific pre-decision status.

It is intentionally conservative:

- private repository contents were inspected read-only;
- this report records only public-safe conclusions;
- no private source material, private career evidence, company-confidential detail, or raw provenance is copied here;
- no repository visibility changes are authorized.

## Live status

| Repository | Current visibility | Public-safety conclusion | Automation-safe work remaining | Owner decision still required |
| --- | --- | --- | --- | --- |
| Engineering Labs | private | Structurally suitable for eventual full-repository publication, but release gates are incomplete | license; GRS consumer adoption; community/governance surfaces; executable green quality + secret gates; metadata | approve full-repo publication timing vs keep private |
| Engineering Handbook | private | Full-repository publication is **not yet public-safe** because personalized career-context surfaces are mixed with the public-suitable knowledge system | define/sanitize public boundary; license; GRS consumer adoption; community/governance surfaces; executable green validation + secret gates; metadata | full repo after sanitization vs separate sanitized/public projection vs keep private |
| Career Intelligence | private | Canonical repository should remain private by default; public website/API projection is the safer public artifact | projection-only audit; explicit public-source boundary if ever needed; licensing only for an actual public artifact; owner-lane governance | keep canonical repo private vs create sanitized public-source artifact vs later dedicated full-repo review |
| Haversine | public | M4 visibility gate not applicable | deeper OSS engineering belongs to M5 | none for M4 |

## Engineering Labs — live audit

Positive evidence:

- repository remains private and owner-controlled;
- README/public-safety documentation is intentionally written for synthetic, educational, public-safe use;
- product identity and employer-attribution restrictions are explicitly documented;
- quality and full-history secret-scan workflows exist.

Current release blockers observed on the default branch:

- no explicit license file;
- no repository-local GRS consumer manifest;
- no PR template;
- no issue taxonomy;
- no CONTRIBUTING.md;
- no SECURITY.md.

A previously open Node-24 Actions maintenance PR was rebased onto the current default branch without dropping later quality checks. Its branch is mergeable, but the fresh Quality and Secret Scan jobs currently fail before runner execution. Because those failures have no executed steps, they are CI-infrastructure/prestart evidence rather than proof of a code defect. They must not be treated as a green public-release gate.

**M4 recommendation:** continue preparing Engineering Labs for a full-repository public release, but do not request the owner visibility decision until the owning lane has closed the release blockers and executable CI is green.

## Engineering Handbook — live audit

Positive evidence:

- theory, mechanisms, labs, validation tooling and generic engineering content are strong public-knowledge candidates;
- repository-local validation and full-history secret scanning exist;
- the knowledge system has clear bounded-context and authority documentation.

Public-safety finding:

- the repository contains a dedicated personalized area with career evidence, gap, knowledge and learning maps;
- those surfaces are useful privately but are not equivalent to generic public engineering theory;
- the repository also contains automation/operating material whose publication boundary should be deliberate rather than assumed.

This means the current repository shape does **not** justify a blind private-to-public flip.

Current release blockers observed on the default branch:

- no explicit license file;
- no repository-local GRS consumer manifest;
- no PR template;
- no issue taxonomy;
- no CONTRIBUTING.md;
- no SECURITY.md.

The Node-24 Actions maintenance PR was also rebased onto the current default branch. It is mergeable, but fresh validation and secret-scan jobs fail before runner execution with no executed steps, so the current signal is CI-infrastructure/prestart rather than a verified code failure.

**M4 recommendation:** prefer a sanitized/public projection unless the owning Handbook lane first separates or sanitizes personalized/private-context surfaces and then proves the full repository is public-safe.

## Career Intelligence — live audit

The repository remains private and actively developed by its owning Career Ecosystem lane.

The canonical system is intentionally broader than its public projection. M4 must preserve:

```text
private canonical career system
  -> validated public-safe projection
    -> public website / API / selected documentation
```

The canonical repository should therefore remain private operationally unless a later dedicated public-source design proves that private source records, provenance, internal identifiers, private workflow material and unsupported claims cannot leak.

**M4 recommendation:** keep the canonical repository private; treat the public projection as the portfolio artifact. A separate sanitized public-source artifact can be considered later if it creates real engineering value.

## What is now ready for owner decision

The owner packet can now be interpreted with stronger evidence:

1. **Engineering Labs** — recommended target: eventual full-repository public release after owning-lane gates are green.
2. **Engineering Handbook** — recommended target: sanitized/public projection first; full-repo publication only after explicit private-surface sanitization.
3. **Career Intelligence** — recommended target: keep canonical repository private; public website/API remains the public artifact.

No option is approved by this audit.

## Remaining M4 acceptance work

Before M4 can close:

- Engineering Labs owning lane must provide actual release readiness or the owner must explicitly choose to keep it private.
- Engineering Handbook owning lane must define and validate the publication boundary.
- Career Intelligence publication strategy must be explicitly selected by the owner.
- Any repository intended to become public must have an explicit license and executable green release/security gates.
- Visibility changes remain human-only.

## Decision

M4 is the current strategic milestone.

Automation-safe analysis and decision preparation are substantially complete. The remaining critical path is now a combination of owning-lane remediation and explicit owner publication choices, not additional central speculation.
