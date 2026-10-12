# Engineering Governance v1 — Registry Specification Draft

Status: DRAFT — no adoption requirement yet
Date: 2026-10-12

## Purpose

Provide one deterministic discovery index for the seven governed repositories without creating a second status database.

## Discovery principle

Governance standardizes **how to discover canonical sources**, not where every repository must place them. Existing local file paths remain valid. The registry points to them; it does not force a universal `ROADMAP.md`, `TASKS.md`, `AGENTS.md`, or other filename.

The registry should answer only:

- which repositories are in scope;
- which default branch is canonical;
- which bounded domain owns the repository;
- which GRS class applies;
- where an authorized agent should look for local roadmap, agent rules and evidence entrypoints.

It must not store:

- mutable roadmap percentages;
- current PR numbers;
- current SHAs as durable truth;
- current CI conclusions;
- runtime scheduler state;
- copied domain task status.

## Proposed record shape

```json
{
  "repository": "DaniilSydorenko/haversine-geolocation",
  "default_branch": "master",
  "domain_owner": "haversine",
  "grs_class": "oss-library",
  "discovery": {
    "roadmap": "docs/roadmap/haversine-v2-human-roadmap.md",
    "agent": null,
    "governance_manifest": ".github/repository.json"
  }
}
```

## Candidate schema rules

- schema version is explicit;
- exactly seven repository records for Governance v1 scope;
- repository names are unique;
- each default branch is a non-empty string;
- each domain owner is from a small explicit enumeration;
- each GRS class must exist in the current GRS class taxonomy;
- discovery paths are repository-relative strings or null;
- no live status/progress fields are allowed;
- no credential, runtime or private-data values are allowed.

## Validation strategy

Reuse the existing GRS Control Plane.

Proposed read-only checks after owner approval and pilot acceptance:

1. registry JSON/schema validation;
2. repository names unique and in approved scope;
3. declared GRS class exists;
4. discovery pointer shape is valid;
5. optional live check confirms declared default branch still exists;
6. optional live check confirms required discovery path exists.

Live branch/path checks must not write repository state.

## Adoption rule

The registry is an index. A referenced repository remains authoritative for the content behind each pointer.

If the registry conflicts with repository live state, the registry is stale and must be repaired; it does not override the repository.

## Rollout gate

Do not create a required machine-readable registry or enforce local discovery entrypoints until the owner approves the GOV-M02 authority deltas. Any approved adoption must preserve repository-local file locations and avoid copying mutable status.
