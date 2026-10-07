# GRS rollout preflight — Career Intelligence

Date: 2026-10-07
Status: **CENTRAL READINESS EVIDENCE ONLY — private canonical-data repository**

## Scope

This preflight records live GitHub-governance surfaces observed read-only on `DaniilSydorenko/career-intelligence`.

It does not authorize consumer-repository changes, public visibility, or publication of private career data.

## Classification

- GRS class: `platform`
- maturity: `active`
- visibility: `private`
- portfolio intent: flagship / pin candidate
- central manifest: `grs/pilots/career-intelligence.repository.json`

## Live measured surfaces

| Surface | Observed | Interpretation |
| --- | --- | --- |
| README.md | present | strong current engineering/public-safety explanation |
| repository description | not set | metadata gap |
| topics | not set | metadata gap |
| .gitignore | present | baseline surface present |
| secret-scan workflow | present | secret-hygiene surface present |
| validation workflow | present | project validation surface present |
| LICENSE variants | not observed | required before a public `platform` release decision |
| PR template | not observed | required by GRS `platform` profile |
| issue taxonomy | not observed | required by GRS `platform` profile |
| CONTRIBUTING.md | not observed | recommended |
| SECURITY.md | not observed | recommended |
| repository consumer manifest | not observed | GRS adoption not yet installed in consumer repo |

## Public-safety boundary

Career Intelligence is not a normal public-source candidate.

Its README explicitly states that the public site is a projection of a private career ledger and that public copy must not introduce recruiter names, raw messages, compensation, private interview material, internal identifiers, or unsupported metrics. UNKNOWN remains UNKNOWN.

Therefore the release model must preserve:

private canonical career ledger
→ validated/public-safe projection
→ public website/API surfaces

and must never treat repository visibility as equivalent to public-data approval.

## Ownership

Career Ecosystem Autopilot owns Career Intelligence domain engineering and canonical evidence semantics.

GitHub Autopilot is read/audit only for domain content. Missing governance surfaces are evidence, not permission to modify the repository from this lane.

## Recommended readiness sequence

1. Keep the repository private while Career Ecosystem work is active.
2. Define the exact public repository boundary: full repository, sanitized projection, or separate public artifact.
3. Complete a private-data / secrets / provenance exposure audit.
4. Make licensing explicit before any public release.
5. Install GRS consumer governance only through the owning Career Ecosystem lane or an explicitly authorized governance-only PR.
6. Add repository metadata only when the intended public identity is decided.
7. Require owner approval for any visibility change.

## Current conclusion

Career Intelligence is technically mature enough to be a strong engineering flagship candidate, but public readiness is primarily a data-boundary and publication-design problem, not a missing-code problem.

No private-to-public action is authorized by this preflight.
