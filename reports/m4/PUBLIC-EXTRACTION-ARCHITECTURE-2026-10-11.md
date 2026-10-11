# M4 — Public Extraction Architecture and Sensitive-Surface Audit

Date: 2026-10-11
Status: **ACTIVE — publication intent expanded; physical separation required before visibility changes**

## Goal

Maximize the public engineering value of Daniil Sydorenko's ecosystem without exposing private career data, employer-confidential material, interview-process material, raw source records, credentials, or internal-only provenance.

The publication rule is now:

> Code, architecture, tests, public documentation and synthetic examples are public by default.
> Personal/private/company data and private career-preparation overlays are physically separated and remain private.

No repository visibility change is authorized by this report.

## Engineering Labs

### Recommendation

Target: **public canonical repository** after extraction and final history/readiness checks.

### Strong public surfaces

Keep public:

- application and package source;
- Mission → Stage → Scenario → Task architecture;
- M001 aircraft-tracking mission and synthetic scenarios;
- tests, CI, security/secret-scan workflow;
- architecture/deployment/learning-system documentation;
- design tokens and shared packages;
- public-safety rules;
- ecosystem manifests/contracts that contain no private evidence;
- generic technical exercises and mechanism labs.

These are directly useful portfolio evidence.

### Private or strategically non-public surfaces

Extract before publication:

- company-targeted interview preparation under `docs/reference-sources/`, especially Booking / Revolut / Kraken targeting;
- interview answer banks under `docs/interview/`;
- legacy interview-answer archives under `docs/archive/legacy-learning/interview/`;
- task material whose primary purpose is candidate interview scripting rather than the public learning product, including interview-answer communication tasks;
- future personal behavioral stories or employer-specific preparation if added.

This material is not necessarily confidential, but it exposes job-search strategy, rehearsed answers and target-company preparation and dilutes the product/engineering signal.

### Destination

Do not create a public clone.

Move personal interview-preparation content into the private career-preparation/data plane. Engineering Labs remains the one canonical public practice product.

### History gate

Current-tree cleanup is insufficient if removed material exists in Git history.

Before public visibility:

1. inspect full history for private/preparation content and PII, not only secrets;
2. if sensitive history exists, perform a reviewed history rewrite while the repository is still private;
3. verify no required public engineering history is accidentally lost;
4. rerun full-history secret/content scans on the rewritten history.

A history rewrite is owner-gated and must not be performed automatically.

## Engineering Handbook

### Recommendation

Target: **public canonical repository**.

Do not maintain a separate sanitized Handbook clone.

### Strong public surfaces

Keep public:

- canonical engineering theory under `handbook/`;
- labs/micro-experiments that are mechanism-focused;
- diagrams and glossary;
- validation/build tooling;
- machine-readable topic/coverage manifests;
- ecosystem architecture and ADRs;
- domain authority, CI-boundary, integration-event, MCP and evidence-candidate architecture;
- public automation/runbook material that describes generic repository operation.

This is strong senior/system-engineering evidence.

### Private personalized overlay

Extract:

- `daniil/evidence-map.md`;
- `daniil/gap-map.md`;
- `daniil/knowledge-map.md`;
- `daniil/learning-roadmap.md`;
- future Daniil-specific evidence classifications, weakness/gap prioritization and career planning.

These files expose personal evidence gaps, employer mappings and career strategy. They belong to Career Intelligence/private learning state, not the public theory authority.

### Required refactor

The public Handbook currently references Daniil-specific mapping in its Definition of Done and autonomous worker instructions.

Refactor the contract so Handbook owns generic theory/practice metadata, while a private external overlay supplies:

- current personal knowledge state;
- evidence classification;
- gap priority;
- target practice priority.

The worker may consume that overlay through a private CI/MCP/API boundary when available. The public repository must not require a checked-in personal map.

### History gate

Because `daniil/` already exists in repository history, deleting it from current main would not make the historical repository private-safe.

Before public visibility, evaluate a path-filtered history rewrite (for example, removing `daniil/` from all historical commits) while preserving the public theory history. This is owner-gated.

## Career Intelligence

### Recommendation

Target: **public canonical engineering/platform repository + private data plane**.

The code repository should not remain private merely because the product processes private career data.

### Strong public surfaces

Keep public:

- application/domain architecture;
- schema and database migrations;
- canonicalization algorithms;
- importer framework;
- public projection policy;
- API/BFF and CLI;
- provenance/confidence/uncertainty model;
- ecosystem contracts and adapters;
- tests with synthetic fixtures;
- public website/UI;
- security/redaction rules;
- deployment examples without real credentials;
- public-safe architecture documentation.

This is the highest-value system-design story in the ecosystem.

### Private data plane

Never commit to the public repository:

- raw Gmail / LinkedIn / Takeout exports;
- raw recruiter messages or thread text;
- compensation values/offers/bands;
- private interview questions, feedback text or take-home material;
- private employer/customer/internal identifiers or URLs;
- raw Career Intelligence workbook;
- canonical private ledger records;
- raw Evidence / Observation / SourceRecord payloads;
- private recruiting pipelines and active opportunity state;
- credentials, tokens and production connection strings;
- private uncertainty/reconciliation notes;
- private company material.

Recommended runtime/storage separation:

```text
PUBLIC GitHub repository
  career-intelligence
    code / schemas / migrations / policies / tests / synthetic fixtures / public UI
              |
              | DATABASE_URL / private runtime boundary
              v
PRIVATE DATA PLANE
  private PostgreSQL canonical ledger
  + encrypted/private raw-source vault
  + private import manifest/config
              |
              | projection policy
              v
PUBLIC PROJECTION API / website
```

### Current-tree issues to fix before publication

The raw workbook itself is already outside Git and local DB files/secrets are ignored — good.

However several checked-in files currently expose private-derived or internal-detail information that needs deliberate classification/refactoring:

1. `packages/importer/src/constants.ts`
   - exact private workbook filename;
   - exact workbook SHA-256;
   - exact reconciliation counts.
   Move these values to a private import manifest stored beside the private source artifact. Keep only the public manifest schema and synthetic test values in Git.

2. `docs/PUBLIC_ACTIVATION.md`
   - internal entity keys;
   - exact activation allowlists;
   - deferred employer/project names and internal story IDs.
   Replace public documentation with synthetic/example IDs or public-safe labels. Keep real activation state in the private ledger/config.

3. `src/data/recruiting-observatory.ts`, `data-footprint.ts`, `decision-calibration.ts`, `feedback-intelligence.ts`, `evidence.ts`, `timeline.ts`
   - contain real career-derived aggregates, personal history and/or interview-feedback-derived material.
   Each value must be either:
     a. explicitly approved public projection returned by the private projection layer; or
     b. moved out of source control.
   Long term, real public content should come from the projection API rather than hard-coded private-derived source modules.

4. `src/lib/career-fixtures.ts`
   - currently mixes real company labels with synthetic/example timeline data.
   Convert fixtures to fully synthetic entities so test data cannot be mistaken for canonical career truth.

5. Public profile identity fields are intentionally public and may remain.

### Private import manifest

Avoid a duplicate private code repository.

Use a non-versioned/private import manifest next to the source artifact, for example:

```text
.local/migration/
  source.xlsx
  manifest.json
```

The public repository defines the manifest schema. The private manifest supplies source filename, expected hash, reconciliation expectations and other source-specific values.

For hosted operation, canonical data belongs in private PostgreSQL; raw immutable sources belong in private/encrypted object storage or another controlled vault.

## Cross-repository rule

Do not solve publication by maintaining duplicate public clones.

Preferred architecture:

- Engineering Labs: one canonical public product repository + private prep overlay elsewhere.
- Engineering Handbook: one canonical public theory repository + private personal-learning overlay elsewhere.
- Career Intelligence: one canonical public code/platform repository + private data plane.

The only duplicated material should be rebuildable public projections, never a second canonical source.

## Sensitive-content classes

### MUST STAY PRIVATE

- secrets/credentials;
- raw personal communications;
- compensation/offers;
- raw private interview material;
- active recruiting pipeline;
- raw source records/evidence payloads;
- employer/customer internal material;
- private personal gap/evidence maps;
- canonical private career ledger.

### PUBLIC AFTER DELIBERATE APPROVAL

- selected employment/project facts;
- selected career stories;
- aggregate recruiting research;
- public-safe feedback themes;
- public portfolio metrics;
- public profile identity/contact destinations.

These must pass the Career Intelligence projection policy and must never become public merely because they exist in a public repository.

### PUBLIC BY DEFAULT

- generic source code;
- architecture;
- tests;
- synthetic fixtures;
- schemas;
- validation tooling;
- CI;
- generic learning material;
- generic engineering documentation;
- public-safe ecosystem contracts.

## Pre-public history and provenance gate

Secret scanning alone is not enough.

For each candidate repository:

1. current-tree PII/private-content audit;
2. full Git-history secret scan;
3. full Git-history private-content/PII path and keyword audit;
4. inspect deleted historical artifacts;
5. inspect large/binary historical blobs where relevant;
6. decide whether a path-filtered history rewrite is necessary;
7. rerun all scans after rewrite;
8. verify build/test/GRS on final exact head;
9. add/confirm license, SECURITY, CONTRIBUTING and public metadata;
10. owner explicitly approves visibility change.

## M4 closeout definition

M4 is DONE only when:

- all three repositories have an explicit public/private architecture;
- private content is physically separated from public code;
- current tree is public-safe;
- history is public-safe or deliberately rewritten;
- real CI and security gates are green;
- public-facing documentation tells one coherent ecosystem story;
- final visibility changes remain owner-controlled.

The goal is not to hide the ecosystem. The goal is to make the **engineering system maximally public while keeping the private data plane actually private**.
