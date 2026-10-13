# Governance v1 — Owner decision package (2026-10-13)

**Decision required at [issue #56](https://github.com/DaniilSydorenko/.github/issues/56).** This is a proposal, not approval. Audit Freeze removal does not approve C01–C07.

## Existing active controls (not awaiting reapproval)

- GRS schema, class profiles, pilot fixtures, validator, class-policy drift check, publication-boundary validation and GRS Control Plane CI.
- Default-deny Autopilot merge policy, exact-head/required-CI/owner-gate constraints.
- GitHub default branch as accepted engineering artifact source; repository-local roadmaps remain domain-owned.
- Existing secret scan and repository-specific CI where implemented. These are not proof of universal full-history clearance or seven-repo conformance.

## Proposed new binding semantics requiring explicit owner decision

| Contract | Existing baseline | Proposed binding addition |
| --- | --- | --- |
| C01 Source of Truth | Local roadmap/authority and central discovery registry | Required machine-verifiable discovery/authority metadata where approved; no duplicated mutable status |
| C02 Roadmap Integrity | Local roadmaps and stable milestone IDs | Evidence-based defect traceability and explicit authority for status updates |
| C03 Agent Execution | Default-deny merge safety, worker ownership | Bounded task scope/collision checks and explicit worker policy-consumption evidence |
| C04 Evidence & Completion | PR/CI/merge evidence | Uniform stage vocabulary (planned/implemented/tested/merged/deployed/released/runtime-verified) without changing domain acceptance |
| C05 Cross-Repository Authority | HQ vs Control Plane vs domain ownership | Machine-checkable owner boundaries; no product takeover |
| C06 Security, Reliability & Cost | GRS, secret scans, least privilege | Adoption/equivalence checks with documented exceptions and no new service by default |
| C07 Reconciliation & Reporting | Canonical roadmaps, reports and telemetry boundaries | Read-only drift reporting, freshness/authority checks; no parallel status database |

## Explicit adoption boundaries / exceptions for decision

1. **Seven engineering repositories** are the current discovery scope; the eighth active profile repository is a separate lightweight class/exception decision, not silently mandatory.
2. **Private repositories:** do not require open-source license, public publication artifacts or public-only metadata.
3. **Haversine:** retain OSS release and package-specific CI; central GRS checks must not own releases.
4. **ListingKit and Career Intelligence:** preserve domain implementation, data/PII boundaries and local acceptance.
5. **Control Plane:** preserve scheduler/runtime authority and authenticated write-job requirements; do not disable required credentials blindly.
6. **Archived repositories:** inventory/read-only by default; no forced migration or branch deletion.
7. **Existing local GRS manifest coverage is 1/7**, not seven-repository compliance. GOV-M06 100% means discovery mapping only.

## Always owner-gated

Repository visibility; history rewrites; credentials/revocation; stable release publication; destructive branch cleanup enablement; product-domain acceptance; new mandatory cross-repo enforcement before approval.

## Requested owner response

Choose **approve C01–C07 as scoped**, **approve with enumerated revisions/exceptions**, or **defer**. Record the exact accepted version/commit, exceptions and effective scope in issue #56. Only then start owner-scoped enforcing adoption PRs.

## Acceptance and evidence

**GOV-M07:** repeatable seven-repo discovery + manifests (or approved exceptions), class-profile audits, exact-head validated CI, worker policy-version-to-execution trace, Haversine full engineering cycle and collision preflight. Distinguish discovery, manifest, class compliance, CI enforcement and operational acceptance.

**GOV-M08:** explicit #56 approval, documented exceptions, one complete authorized Haversine pilot (or justified block), three repeatable engineering rounds, reconciled domain/HQ roadmaps, owner gates preserved, freeze/no-new-machinery decision.

**Unknown until inspected:** live branch protection/rulesets, complete exact-head CI for every domain, actual external scheduler prompts and policy-loading, historical scan completion, private repo-specific exemptions.

**Lean 12-stage protocol:** consequential work follows full sequence; low-risk mechanical tasks may report concisely while still checking fresh repo/PR state, collisions, exact-head CI, owner gates, post-merge verification and roadmap updates when relevant.

## Next three high-value PRs (sequence, not authorization)

1. **HQ #79 consolidation evidence closeout:** verify accuracy, deduplicate with existing GOV-M07/M08 items, integrate after applicable review; do not add milestones.
2. **HQ GRS conformance reporter (read-only):** reuse existing registry/validator/audit code to emit five distinct adoption dimensions; tests, no enforcement and no new scheduler. Owner gate before required CI rollout.
3. **Haversine GRS pilot hardening:** domain-owned narrow PR for versioned central GRS checkout and credential minimization, plus exact-head validation and post-merge evidence; avoid release changes. If Haversine ownership not delegated, hand off rather than mutate.

Worker policy consumption needs a separate read-only entrypoint audit before claiming runtime integration.
