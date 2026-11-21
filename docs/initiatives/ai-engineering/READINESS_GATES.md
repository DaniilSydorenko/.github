# AI-ENG readiness contract — v1 (2026-11-18)

## Meaning of status

Never infer LIVE_READY from a green PR CI. Report five independent levels:

| Gate | Trigger | Proof | Failure |
| --- | --- | --- | --- |
| G0 change sanity | Every relevant PR | Python compile and bounded local fixtures | FAIL |
| G1 safety contracts | Every control-plane PR | singleton race/replay, fail-closed inventory, transition tests | FAIL |
| G2 integrated chain | Before live candidate and after integration changes | executor acquires durable lease before model, protected publisher and exact-head verifier, adversarial end-to-end mocks | BLOCKED until demonstrated |
| G3 operational enforcement | Before each live pilot and after permission/config changes | authenticated effective rulesets, exclusive writer, credential access, provider hard budget, no bypass routes | BLOCKED if unknown |
| G4 live admission | Immediately before each paid invocation | fresh owner scope, exact issues/paths, collisions, stable SHA, lease ownership, remaining provider budget | STOP if unknown |

Statuses: `PASS`, `FAIL`, `BLOCKED` (not implemented/not evidenced),
`UNKNOWN` (unavailable/stale). `SKIPPED` is not PASS. Never collapse
five gates into one green badge.

## Fast feedback after each implementation

Run from repository root:

```bash
python3 docs/initiatives/ai-engineering/fast_readiness_gate.py
```

This zero-network, zero-model G0/G1 gate runs the #164 offline inventory,
queue, singleton and CAS regression tests; it reports JSON with
`live_admission: BLOCKED` **even when it passes**. It is the first step of
`offline-contract` in the PR workflow. No provider credentials required.

Escalate G2 after changes to executor/publisher/lease wiring. Run G3/G4 only
when preparing a live pilot or when external configuration changes. Do not
run expensive network audits after every documentation-only edit.

## Open blockers and minimal work order

1. Confirm effective lease-ref writer and non-fast-forward/deletion protection,
   Integration identity and all model credential launch paths; do not alter
   permissions or rulesets without separate owner approval.
2. Adapt existing Cursor lease state machine to OpenHands issue identities,
   strict replay and terminal evidence, without duplicating state stores.
3. Parameterize legacy #220 executor/verifier/publisher for #216/#217/#226.
4. Add protected workflow integration with lease before model credential and
   independent Draft PR exact-head CI/security verification before release.
5. Test races, network ambiguity, crash recovery, replay, overlapping PRs,
   stale head and provider cap exhaustion; STOP on missing proof.
6. Diagnose scheduled #220 discovery failure separately; avoid conflating
   legacy monitoring failure with new pilot acceptance.
7. Perform G3 authenticated configuration review and G4 preflight; owner
   approves any required security configuration changes and paid launch.

## Change report template

`HEAD SHA | changed paths | G0 | G1 | G2 | G3 | G4 | blockers | next action`.
Cite exact run IDs. Green offline checks cannot close operational blockers.
The current #164 status is **G0/G1 candidate, G2/G3/G4 BLOCKED** until
fresh evidence proves otherwise.
