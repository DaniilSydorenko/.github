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

## Separate Draft PR publisher (second explicit GO)

This is a **separate workflow**, not a continuation that the model can trigger.
The first paid execution remains a verified patch artifact only.

1. Create a dedicated fine-grained GitHub PAT with **only** `DaniilSydorenko/haversine-geolocation` selected; grant **Contents: Read and write** and **Pull requests: Read and write**. Keep expiration short. The control repository's normal `GITHUB_TOKEN` cannot write to the separate Haversine repository.
2. Save it in `DaniilSydorenko/.github` as an **environment secret** named `HAVERSINE_PUBLISH_TOKEN` under the protected `ai-eng-lease-owner` environment. Never paste it in an issue, commit, log, or chat.
3. After a successful paid run, inspect the exact `haversine-issue220-verified-patch` artifact and confirm the content is accurate. Note the successful run's numeric GitHub Actions **run ID**.
4. Manually dispatch **AI Engineering Haversine 220 Protected Draft Publisher** on `main` with `source_run_id`. This is a **second** protected environment approval and a separate human authorization to create a Draft PR.
5. Publisher checks the source run's repository, actor, workflow path, event, successful live job, first attempt, and control-branch SHA. It downloads only the named artifact, checks the one-file patch, replays it, rechecks Haversine PR collisions and base SHA, then creates a **Draft** PR.
6. Inspect the Draft PR manually. No auto-merge, no release, no next issue. If the source workflow has changed since the run, publisher intentionally rejects it as stale.

**Important:** The dedicated publisher token is needed only for the second step; do not give it to the OpenHands model execution job. No live publisher test should be run without a successful, reviewed source artifact.

**Known limitation:** A fine-grained PAT is an operationally scoped credential, not a short-lived GitHub App installation token. Future hardening should replace it with an installation token and an external lease if multi-agent orchestration expands.
