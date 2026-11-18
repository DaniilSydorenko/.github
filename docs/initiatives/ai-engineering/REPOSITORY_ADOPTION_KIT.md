# Repository adoption kit — AI Engineering Delivery Governance v1

Copy this short local section into a repository-owned `AGENTS.md` **after
reviewing local instructions**. Do not replace domain rules.

## Delivery discipline (local adoption)

For substantial engineering tasks, follow the shared [AI Engineering
Delivery Governance](https://github.com/DaniilSydorenko/.github/blob/main/docs/initiatives/ai-engineering/DELIVERY_GOVERNANCE.md)
**only after that document has merged to main**. Until then this link is
a proposal and not an enforced rule. On new sessions, read local AGENTS.md,
the local canonical delivery plan, existing issue/PR and exact-head CI.
Track work by task ID, blocker register, G0–G4 evidence and bounded AI
sessions. Respect owner-time budget and prefer one bounded PR/agent at a
time. Unknown permissions, cost, writer or release authority => STOP.
Local security, privacy, CI and release policies take precedence.

## Repository bootstrap checklist

- [ ] Confirm repository owner and domain policy; do not overwrite AGENTS.md.
- [ ] Add reviewed local adoption section to AGENTS.md.
- [ ] Define canonical delivery plan path and one existing tracking issue.
- [ ] Establish a fast deterministic zero-model CI test suitable for this repo.
- [ ] Review required checks and rulesets **separately**; never assert that
      a green workflow proves branch protection.
- [ ] Inventory all model/agent launch routes and credentials before enabling
      any autonomous workflow.
- [ ] Verify current PR head, required CI and owner-approved merge before
      marking `MERGED`; verify actual enforcement before `ENFORCED`.
- [ ] Add this checklist to the approved template for *new* repositories.

## Adoption tracking (per repo)

`repo | default_sha | owner | local_rules_reviewed | adoption_pr |
ci_head | state | blockers | last_verified`

State progression: NOT_INVENTORIED → CANDIDATE → PR_OPEN → CI_PASS →
MERGED → ENFORCED. Never jump to ENFORCED because this template exists.

## Boundaries

This is an adoption **template**, not an executable policy or a standing
authorization to write to every repository. Apply through independently
authorized repo-owned changes; do not auto-merge or silently alter secrets,
rulesets, branch protection or paid agent dispatch.
