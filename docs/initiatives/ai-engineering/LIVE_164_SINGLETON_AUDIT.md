# #164 — live singleton and configuration audit (2026-11-18)

**Status: BLOCKED FOR PAID LIVE CHAIN.** This is an evidence register, not an
authorization to launch an agent, merge, alter secrets, or change rulesets.

## Evidence checked

- Central tracking issue: `DaniilSydorenko/.github#164` (OPEN).
- Implementation: Draft PR `DaniilSydorenko/.github#166`, HEAD
  `7a6a28a7c809c99cb90fe043f1455ecea0162a34`; its `offline-contract`
  check concluded SUCCESS. Other manual jobs were SKIPPED, not validated.
- `ai-eng-cursor-lease-v1`: branch API reported `protected: true` and
  `protection.enabled: false`. These are not sufficient to establish
  exclusive writer identity or safe force-push/deletion semantics.
- Repository ruleset `ai-eng-lease-writer` (26090757): ACTIVE, update rule,
  one Integration bypass actor (id 5535339). App identity, token scope,
  effective bypass permissions and launch-path coverage remain UNVERIFIED.
- Repository ruleset `ai-eng-lease-immutable` (26170483): DISABLED; contains
  deletion and non-fast-forward restrictions. Do not silently enable.
- Scheduled readiness workflow run 44130505850 (2026-11-17) FAILED in
  `scheduled-issue220-discovery`; this is not a paid-model failure.
- `github_ref_lease.py`: durable CAS/ref and replay code exists, but is
  documented as NOT wired to Actions/Cursor; its release proof is Cursor
  integration/owner acceptance, not #164 Draft PR acceptance.
- `openhands_sequential_simulation.py`: offline-only, maximum two tasks.
- `openhands_three_issue_gate.py`: offline policy for #216, #217, #226.
- `openhands_live_orchestrator.py` in PR #166: read-only inventory; always
  STOPs rather than authorizing execution.
- `ai-eng-openhands-readiness.yml` and protected publisher workflow:
  existing live #220 runner and publisher share a concurrency group, but
  unrelated workflow groups/external agents do not automatically join it.

## Blocking gates before ANY three-issue paid invocation

1. **Global singleton scope:** enumerate all live OpenHands entrypoints,
   secrets and external launch routes. Demonstrate that only a trusted
   controller can obtain the model credential and that all authorized
   invocations acquire the SAME durable lease. GitHub Actions concurrency
   alone is not a global singleton.
2. **Protected lease writer:** verify effective rulesets, Integration identity,
   bypass grants, token permissions, deletion/non-fast-forward behavior and
   ability to perform atomic ref updates. Unknown or unprotected => STOP.
   Do not modify rulesets or add permissions without separate owner approval.
3. **Lease lifecycle:** adapt the Cursor-specific state machine without
   weakening its replay ledger; release only after independently verified
   Draft PR provenance, exact HEAD, required CI/security and terminal runner
   state. A crash/ambiguous dispatch leaves lease BLOCKED, never auto-expired.
4. **Live integration:** parameterize executor, verifier, publisher and
   protected owner-triggered workflow for the immutable #216/#217/#226
   issue-to-path contract; maintain separated model and publisher tokens.
5. **Cost:** verify shared provider-enforced <=$1 limit and remaining balance
   before each paid attempt; unknown => STOP. A textual budget is not a cap.
6. **Evidence and failure drills:** authenticated live inventory, collision
   checks (including renamed paths), exact-head CI/security, stale base,
   concurrent contenders, lost network, replay, partial PR publication,
   cancellation, and crash recovery must fail closed.
7. **Operational hygiene:** diagnose scheduled #220 discovery failure; classify
   legacy workflows and docs as active/legacy/offline to prevent confusion.
   Do not delete legacy code before dependency review.

## Documentation/configuration source map

- `AGENTS.md`: authority and bounded engineering rules.
- `docs/initiatives/ai-engineering/OPERATING_RULES.md`: singleton, low-burn,
  STOP and permissions contract.
- `docs/initiatives/ai-engineering/ORCHESTRATION_CONTRACT.md`: current
  boundaries and historical lease observations; old protected:false evidence
  is superseded as a point-in-time branch flag by the new protected:true
  observation, NOT by proof of writer exclusivity.
- `docs/initiatives/ai-engineering/HAVERSINE_220_LIVE_PILOT_RUNBOOK.md`:
  legacy #220 manual workflow; not the #164 three-issue runbook.
- `docs/initiatives/ai-engineering/github_ref_lease.py` and
  `lease_ref_protection.py`: CAS and audit implementation.
- `docs/initiatives/ai-engineering/openhands_three_issue_gate.py`:
  #164 queue transition policy.
- `.github/workflows/ai-eng-openhands-readiness.yml`:
  existing #220 execution, offline tests and read-only checks.
- `.github/workflows/ai-eng-haversine220-protected-publisher.yml`:
  separate owner-approved Draft PR publisher for #220.

## Decision

**NO LIVE GO.** No duplicate issues, new scheduler, database, second publisher,
merge, ruleset mutation, new secret or paid pilot are authorized by this audit.
The next smallest deliverable is an offline-tested lease adapter with an
explicit authenticated writer/permission gate, followed by adversarial
workflow integration tests. Only then request separate owner review for
any security-configuration change.
