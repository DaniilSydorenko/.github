# M4 — Career Ecosystem Public Gate

Date: 2026-10-07
Status: **ACTIVE — publication boundaries defined, visibility owner-gated**

## Purpose

M4 decides what can safely become public from the Career Engineering Ecosystem without exposing private canonical data, private company material, unsupported claims, or internal workflow details.

M4 is a publication-design milestone. It is not a permission to flip repository visibility.

## Core rule

```text
private canonical source
  → validated public-safe projection
    → public GitHub / website / documentation
```

Public projection is intentionally narrower than private canonical truth.

## Publication-boundary matrix

| Repository | Current visibility | Public-safe candidate | Must remain private | Required gate before visibility/publication | Owner decision |
| --- | --- | --- | --- | --- | --- |
| Engineering Labs | private | Mission/Stage/Scenario/Task model, synthetic exercises, architecture, selected implementation, public-safe learning artifacts | private company material, real credentials, proprietary examples, any employer-derived data | README/status current; synthetic/public-safe examples only; explicit license; GRS consumer green; quality/build/secret gates green; metadata ready | approve public repository timing |
| Engineering Handbook | private | canonical engineering theory, mechanism experiments, diagrams, glossary, generic practice requirements | personalized career maps where they reveal private evidence/history; private company material; private planning notes | decide public content boundary; explicit license; generated artifacts checked; validation + secret scan green; GRS knowledge consumer green; metadata ready | approve whether full repo or sanitized public projection |
| Career Intelligence | private | recruiter-first profile, public-safe case study, approved career projection, public API/BFF projection, architecture that does not expose private ledger contents | raw source records, recruiter messages, compensation, private interview material, internal identifiers, raw provenance/evidence ledger, unsupported metrics, company-confidential material | public-data audit; projection-only verification; explicit licensing decision; GRS platform consumer green; tests/typecheck/build/secret gates green; release checklist; owner approval | choose full-repo vs sanitized/public artifact and approve publication |
| Haversine | public | current OSS library, governance, documentation, releases | secrets/private maintainer data | M3 governance already satisfied; deeper quality work belongs to M5 | no M4 visibility decision needed |
| Ladvero | private | later product-facing public projection if product owner approves | active product/IP/private roadmap/config/secrets | separate Ladvero public-safety/release process | separate owner gate |

## Engineering Labs boundary

The current README already states a public-safe intent and synthetic examples. The canonical learning model is:

```text
Mission → Stage → Scenario → Task
```

M4 publication work should preserve that model and avoid employer attribution.

Allowed public emphasis:

- deliberate practice;
- frontend/system engineering;
- protocols/security/AI workflows;
- architecture and testing;
- synthetic failure scenarios;
- public-safe technical artifacts.

Not allowed:

- Klarna branding or implied endorsement;
- proprietary production examples;
- real credentials, customer data, or internal telemetry;
- claims that synthetic Lab work equals production experience.

## Engineering Handbook boundary

The Handbook is suitable in principle for public knowledge publication, but private personalization must be reviewed before full-repository visibility.

Public-safe emphasis:

- theory;
- mechanisms;
- trade-offs;
- failure modes;
- security/performance/observability;
- generic experiments;
- clearly labeled evidence levels.

Potentially private/sanitized areas:

- personalized career maps;
- evidence classifications tied to private source material;
- private roadmap notes;
- employer-specific detail not already public-safe.

Licensing becomes an explicit gate before public release.

## Career Intelligence boundary

Career Intelligence requires the strictest separation.

The repository already defines the correct principle:

> The site is a projection of a private career ledger.

The following are public-safe only after validation:

- selected career facts already approved for public projection;
- recruiter-first profile content;
- public project/case-study narratives;
- public architecture and data-projection design;
- approved role/skill projections;
- public API responses constrained to approved subjects.

The following must not be published from the canonical ledger:

- raw recruiter messages;
- raw interview material;
- compensation;
- private source records;
- private evidence/provenance graph;
- internal identifiers that expose private records;
- unsupported metrics or inferred claims;
- private company/confidential material.

Repository visibility must not be used as a shortcut around these rules.

## Required M4 acceptance gates

M4 can be closed when:

1. every candidate has an explicit public/private boundary;
2. licensing decisions are explicit for repositories intended to become public;
3. public READMEs/status text are ready;
4. secret/public-data audits are green;
5. GRS consumer validation is green or an explicit owner-lane plan exists;
6. metadata/pin role is decided;
7. owner has made the required publication/visibility decisions;
8. no private-to-public change occurs automatically.

## Current owner decisions still required

- Engineering Labs: approve public timing after owner-lane readiness evidence is green.
- Engineering Handbook: choose full-repo publication vs sanitized public projection, then approve timing.
- Career Intelligence: choose full-repo publication vs separate/sanitized public artifact; default remains private until explicitly approved.
- Ladvero: no decision in M4; keep under separate product release ownership.

## Decision

M4 starts with **boundary clarity before visibility changes**.

No private repository is authorized to become public by this document.
