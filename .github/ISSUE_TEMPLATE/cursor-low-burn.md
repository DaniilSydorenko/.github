---
name: "AI task · Low-Burn (optional)"
about: "One scoped, verifiable change for an agent; no automatic Cursor launch"
title: "[AI TASK] "
---

<!-- Optional cross-repo template. Local AGENTS.md, security, owners and CI always take precedence. Do not @cursor automatically. -->

### Outcome + evidence
One logical problem, observable symptom (or link) and the expected result. No full chat transcript.

### Execution scope
- Owner / repo:
- Existing Issue/PR / dependency (or none):
- Baseline SHA (refresh before editing):
- Read first: local mandatory rules + 2–4 relevant files
- Allowed paths:
- Forbidden paths / owner gates:

### Acceptance
- Deterministic reproduction or expected behavior:
- Focused tests and existing required exact-head CI/security checks:
- Proof of done (not just PR opened):

### Low-Burn limits
- One active writer and one scoped PR/branch; default low-cost model.
- One implementation + at most **two evidence-based corrections**; stop after repeated equivalent failure.
- No repo-wide scanning, extra subagents, unrelated changes, blind retries or duplicate agent launches without a reason and approval.
- STOP and report BLOCKED/INCONCLUSIVE on scope drift, missing permission, unobservable budget or safety conflict.
- Token/$ limits in text are **soft**, not technically enforced. Do not trade off tests/security for savings.

### Completion summary (after execution)
Outcome · PR + exact HEAD · tests/CI links · blocker/approval · next action.
Usage **only if measured from authorized Cursor provider**:
`input / output / cache-read / cache-write / total tokens`; `charged cost` if verified.
Otherwise: **tokens UNKNOWN; charged cost UNKNOWN**. No invented estimates or pasted secrets.

<!-- Rules: https://github.com/DaniilSydorenko/.github/blob/main/docs/initiatives/ai-engineering/OPERATING_RULES.md -->
