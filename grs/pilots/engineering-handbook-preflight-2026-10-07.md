# GRS rollout preflight — Engineering Handbook

Date: 2026-10-07
Status: **CENTRAL READINESS EVIDENCE ONLY — consumer repository remains private and separately owned**

## Scope

This preflight records deterministic GitHub-governance surfaces observed read-only on `DaniilSydorenko/engineering-handbook`. It does not authorize consumer-repository changes or visibility changes.

## Pilot classification

- GRS class: `knowledge`
- maturity: `active`
- visibility: `private`
- portfolio intent: flagship / pin candidate
- central manifest: `grs/pilots/engineering-handbook.repository.json`

## Live measured surfaces

| Surface | Observed | GRS interpretation while private |
| --- | --- | --- |
| README.md | present | PASS |
| .gitignore | present | PASS |
| secret-scan workflow | present | PASS |
| LICENSE variants | not observed | conditional; not REQUIRED for private knowledge |
| PR template | not observed | WARN / recommended |
| issue taxonomy | not observed | WARN / recommended |
| CONTRIBUTING.md | not observed | WARN / recommended |
| SECURITY.md | not observed | not a deterministic knowledge-class control in GRS v1 |

## Safety / ownership

Engineering Handbook has its own Career Ecosystem writer. GitHub Autopilot is read/audit only for that repository. Missing surfaces are evidence, not permission to write consumer docs/config. Private-to-public visibility remains owner-gated.

## Next central unit

After the Engineering Labs R10 unit is merged and remote-verified, explicitly validate this pilot manifest in the central GRS control-plane workflow, require GREEN CI, and keep any consumer remediation with the Engineering Handbook owner.
