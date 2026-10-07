# M4 — Private Actions prestart blocker

Date: 2026-10-08  
Status: **BLOCKED BY CI INFRASTRUCTURE — no code-failure evidence**

## Scope

This note records the current GitHub Actions blocker affecting the private Engineering Labs and Engineering Handbook maintenance PRs.

It exists to prevent repeated blind retries and to distinguish infrastructure failure from repository failure.

## Engineering Labs

PR: `#8 — chore(security): upgrade pinned Actions to Node 24 releases`

Live branch state at this check:

- base: `main`
- head: `e455bc2e025f1e06b59cc21b3bb4eefa8c32a151`
- compare state: ahead by 1, behind by 0
- PR mergeable: true
- changed surface: `.github/workflows/quality.yml` only

Fresh retry evidence:

- Quality workflow run `37684474686`, attempt 3: **failure**
- Secret Scan workflow run `37684474646`, attempt 3: **failure**
- both jobs completed without executed steps;
- returned job payloads contain `steps: null`.

Interpretation: **SYSTEM / CI_INFRA / PRESTART**.

The retry did not produce evidence of a failing install, test, build, lint, typecheck or secret scan.

## Engineering Handbook

PR: `#52 — chore(security): upgrade pinned Actions to Node 24 releases`

Live branch state at this check:

- base: `main`
- head: `75a497c4f39cdadc0991f485411ee6ae5674e27b`
- compare state: ahead by 1, behind by 0
- PR mergeable: true
- changed surface: `.github/workflows/handbook-validate.yml` only

Fresh retry evidence:

- Handbook Validate workflow run `37684546924`: **failure**
- Secret Scan workflow run `37684546872`: **failure**
- both jobs completed without executed steps;
- returned job payloads contain `steps: null`.

Interpretation: **SYSTEM / CI_INFRA / PRESTART**.

The retry did not produce evidence of a validation or secret-scan defect.

## Operating rule

Do not repeatedly re-run these exact failed jobs unless one of the following changes:

1. GitHub/private-repository Actions infrastructure is known to have recovered;
2. repository Actions settings or account/billing state changes;
3. the PR head changes;
4. the workflow definition changes for a reason independent of forcing a green result.

A green publication/release gate still requires a fresh run whose actual steps execute and pass.

Do not merge merely because the branches are mergeable, and do not weaken the workflows to bypass the blocker.

## M4 impact

This blocker delays only the executable-CI part of the M4 release readiness for Engineering Labs and Engineering Handbook.

It does **not** invalidate:

- the M4 public/private boundary decisions;
- the Engineering Labs product-readiness gate;
- the Engineering Handbook sanitization/public-projection analysis;
- Career Intelligence remaining private by default.

## Decision

Keep PR #8 and PR #52 open and correctly rebased. Stop retry churn until there is a meaningful change in the infrastructure signal.
