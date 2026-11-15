# Haversine #220 — first real OpenHands pilot runbook

## Scope and boundaries

- **Only** `DaniilSydorenko/haversine-geolocation`, issue **#220**, branch `master`.
- Only `docs/agent-pilot-proof.md` may be created.
- One protected, manually approved, one-shot model invocation; OpenRouter key must have a provider-enforced **$1 total** cap with no reset.
- SDK uses **FileEditorTool only**; no terminal tool, no GitHub write credentials in the execution job.
- This milestone produces a **verified patch artifact**, not a Draft PR, merge, release, or auto-dispatch.
- **No automatic retry** if the model fails or exhausts its allowance.
- The model's instructions and the Python sentinel are not security boundaries. Trust is anchored in GitHub owner-only workflow dispatch, protected environment approval, runner isolation, single-run concurrency, provider key cap, and post-run validation.

## Before the first paid run

1. Review the PR implementing `pilot-live-execute`; require green offline-contract CI and an SDK construction test.
2. Merge the reviewed workflow to `main`. The workflow on PR heads never executes a model.
3. Verify the **same dedicated** `OPENROUTER_API_KEY` is still capped at $1 total, and has no other consumers.
4. Verify no other agent or PR is working on Haversine #220.
5. In GitHub Actions, choose **AI Engineering OpenHands Runner Readiness + Protected Pilot** → **Run workflow** → branch `main` → operation `pilot-live-execute`.
6. GitHub will require separate manual environment approval (`ai-eng-lease-owner`). **Approval launches a potentially paid model call.** Do not approve without intending to spend from the $1 capped key.
7. Inspect the run result and the `haversine-issue220-verified-patch` artifact. Only `PATCH_VERIFIED` with a successful workflow means a valid one-file patch exists. A failed workflow may still have incurred partial model spend.

## After the first run

- **STOP for human review.** Download and inspect the patch, including its Markdown text, and compare it with issue #220 and the repository's actual `distance(a, b)` API.
- This workflow does **not** publish to GitHub. A future independently authorized publisher must verify the same base SHA, exact patch, GitHub PR collision, GitHub App installation permissions, and then create a **Draft** PR only.
- Do not merge the patch, close issue #220, or automatically dispatch another issue.
- If the run fails: preserve logs and run ID, check provider usage, diagnose before requesting another approval. Never auto-retry.
- If the key cap was changed, the budget check must fail closed.

## Known limitations

- A provider-side key limit is a spending boundary, not a guarantee the model finishes within $1. Provider metering may have small delays; inspect actual provider usage.
- The GitHub Actions concurrency lock covers executions of this workflow's live job. It cannot coordinate external agents that ignore this workflow. External single-writer exclusivity is an operational precondition, not cryptographically proven.
- The model can still attempt unexpected file edits; the patch verifier rejects out-of-scope Git changes, but this is not a full OS sandbox.
- The live runner's in-process sentinel is not a secure authorization credential. No untrusted code should execute inside the trusted Python process.
- Publisher integration and end-to-end Draft PR creation remain separate work.
