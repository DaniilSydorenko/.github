# Owner handoff — dedicated GitHub lease-writer App (NO LIVE LAUNCH)

**Status (2026-10-30):** two exact-target rulesets are saved **Disabled**. Existing PR #143 has a read-only credential-path probe and owner-only/manual Actions job. The managed Cursor launch kill switch remains `PILOT_ACTIVATION_ENABLED=False`. This document is an owner security checklist, **not** authority to create an App or spend money.

## One-time owner setup (only after security review / explicit GO)

1. Open [personal GitHub Apps settings](https://github.com/settings/apps/new) under the **DaniilSydorenko personal account**, not another organization. Register an app with an unambiguous name, e.g. `Daniil AI ENG Lease Writer` if available. **Only on this account**; disable webhook subscription; no webhook URL, callback, login or user authorization needed.
2. Repository permissions: **Metadata: Read** (default), **Contents: Read and write**. Set **all other repository, organization and account permissions to None**, including Administration, Workflows, Issues, Actions, Secrets, and PRs. Do **not** grant "All repositories".
3. Install it using **Only select repositories** and select **only** `DaniilSydorenko/.github`. A GitHub App is a distinct account authority; neither Cursor nor ChatGPT Codex Connector can be assumed to be our exclusive writer.
4. Before providing a PEM anywhere, create GitHub **Environment** `ai-eng-lease-owner` in [HQ Environments](https://github.com/DaniilSydorenko/.github/settings/environments). Restrict deployment branches to `main` and configure available owner-controlled environment protection. Under this Environment, add secret **`AI_ENG_WRITER_APP_PRIVATE_KEY`** with the App private key. **Never** put the private key in an Issue, PR, chat, repository file, job logs or ordinary repository variable.
5. Configure these non-secret Actions **variables** through [HQ Actions Variables](https://github.com/DaniilSydorenko/.github/settings/variables/actions): `AI_ENG_WRITER_APP_CLIENT_ID` (App client ID), `AI_ENG_WRITER_APP_ID` (numeric App ID), and `AI_ENG_WRITER_APP_SLUG` (exact App slug). The app's private key remains solely in its environment secret. Keep `AI_ENG_WRITER_PROBE_ENABLED` **unset / false** until environment protections have been checked.
6. Once #143 is explicitly reviewed/merged and the above setup is confirmed, turn on variable `AI_ENG_WRITER_PROBE_ENABLED=true` and **manually** run existing [AI Engineering Singleton Gate Tests](https://github.com/DaniilSydorenko/.github/actions/workflows/ai-eng-singleton-verify.yml) from **main**. The new `owner-app-credential-probe` job mints a **read-scoped**, **single-repository** installation token through official `actions/create-github-app-token`, checks the App identity and exact repository scope with GET-only requests, then automatically revokes the temporary token at job end.
7. Observe `CREDENTIAL_PATH_OBSERVED` only when all metadata checks pass. This **does not** authorize lease writes or Cursor calls. Turn the opt-in variable back off after testing if not needed. Do not report success if the job was skipped.

## Additional GO gates after the probe (NOT implemented/authorized by this document)

- Verify trusted Action key custody and trusted `main` policy; prevent other workflows, branches and human accounts from minting App tokens or calling Cursor outside the approved controller.
- Explicitly review the ruleset writer-bypass actor and App ID; do **not** enable either rule before a positive non-forced fast-forward CAS test strategy and a safe negative push/delete/reset strategy are approved. Immutable ruleset must have **zero** bypass actors.
- Independently re-read real effective GitHub rulesets and protection. Update the **separate** `lease_ref_protection` admission contract only after the ruleset model is actually verified (PR #143's observer is not a launch gate).
- Prove global account-scoped Cursor inventory, a no-bypass launch path, safe billing/subagent limits and task-specific domain-owner approval. The subscription quota and On-Demand Disabled setting are **not** a hard per-run monetary limit.
- Owner explicitly approves **one** pilot task and a separately reviewed change to the code kill switch, then the controller is allowed **one** Cursor POST. STOP after terminal verification; no implicit merge, release, or next Issue. Continuous auto-loop requires its own owner acceptance and real two-task anti-race proof.

## Rollback and emergency stop

Keep both rulesets Disabled and `PILOT_ACTIVATION_ENABLED=False` until the live gates pass. If an App token, key, installation or authority is in doubt, revoke the key / uninstall the App from GitHub account settings, disable the opt-in variable, preserve the lease state for investigation and **never** blindly retry a Cursor POST. Only a manually evidenced recovery may reset a blocked lease.

Docs: [GitHub App registration](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app) · [GitHub App installation](https://docs.github.com/en/apps/using-github-apps/installing-your-own-github-app) · [Environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments) · [App token workflow](https://github.com/actions/create-github-app-token).
