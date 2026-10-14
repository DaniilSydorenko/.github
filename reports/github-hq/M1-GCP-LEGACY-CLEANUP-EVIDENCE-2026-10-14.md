# M1 — Google Cloud legacy credential cleanup evidence (2026-10-14)

## Scope and authority
Owner-confirmed no current Google Cloud or Firebase production applications. This record documents **user-executed** Cloud Shell operations as evidenced by pasted command output, not actions executed by HQ or by a GitHub worker. Seven enumerated legacy projects only; this does not claim account-wide exhaustive inventory.

## Verified credential revocation
- Initial inventory listed **six API keys** across four of the seven projects: two in `auth-5065f`, two in `effective-fire-132313`, one each in `helical-tendril-110308` and `pr-app-1086`.
- Six delete operations were eventually accepted by Google Cloud. Five returned success immediately; `effective-fire-132313` / `portfolio` initially returned `FAILED_PRECONDITION` because Geocoding API usage was detected during the previous seven days. The owner explicitly authorized revocation despite this warning; deletion was then successful with override on **2026-10-14 21:31:03 UTC**.
- The owner ran `gcloud services api-keys list --project=<project> --format='value(displayName)'` for **all seven named projects** after revocation: each completed with **no keys listed**, without errors in the shared output.
- **No API-key values, secrets, tokens, or sensitive Cloud Shell transcripts are recorded here.** The output shared during the conversation did include some deleted key values and must not be pasted into public issues or CI artifacts.

## Verified project deletion-request state
The owner executed and individually confirmed `gcloud projects delete` for each project; all were subsequently independently verified as `DELETE_REQUESTED` at **2026-10-14 21:40:23 UTC**, `ACTIVE=0`, `UNKNOWN=0`:

| Project ID | Post-operation lifecycle |
| --- | --- |
| `spherical-depth-248308` | `DELETE_REQUESTED` |
| `regal-unfolding-232415` | `DELETE_REQUESTED` |
| `vast-cogency-232315` | `DELETE_REQUESTED` |
| `auth-5065f` | `DELETE_REQUESTED` |
| `effective-fire-132313` | `DELETE_REQUESTED` |
| `helical-tendril-110308` | `DELETE_REQUESTED` |
| `pr-app-1086` | `DELETE_REQUESTED` |

Billing was `False` for all seven before deletion. In `auth-5065f`, two GCS buckets existed; a read-only inventory including versions did not find objects. This **does not prove absence** of Firebase Auth, Firestore, App Engine data, hidden dependencies, or recovery risk. `DELETE_REQUESTED` **does not mean permanently purged**.

## M1 acceptance boundary
The canonical M1 task was **old Maps key revoke/dead verification**. This audit establishes that all six keys visible in the seven examined legacy projects were revoked and all seven projects entered shutdown. **The original historical Maps exposure/key ID has not been conclusively matched** to one of these six resource IDs. Thus the precise original exposure closeout is **NOT YET PROVEN** by this record alone. Keep M1 at **98%** pending an authoritative original-finding match, or an owner-reviewed alternate negative verification demonstrating the exposed credential cannot be used. Do not credit M1 100%, increment accepted HQ closure, close other privacy/security gates, or declare account-wide comprehensive cleanup solely from this evidence.

## Exact original Maps key correlation — 2026-10-14 (subsequent evidence)

The original security removal is [archived portfolio PR #1](https://github.com/DaniilSydorenko/frontend-software-engineer-portfolio/pull/1), merged to `master`, modifying `src/app/app.module.ts` to replace an inline Google Maps API key with an empty string. A read-only comparison of the **actual pre-removal key string in PR #1's patch** against the **revoked `portfolio` key value in the owner's Google Cloud deletion response** returned an **exact byte-for-byte match**. The values themselves must **never** be copied into this evidence, roadmap, GitHub comments or build logs.

Thus the specific original Maps key revocation is now **DIRECTLY VERIFIED**, not only risk accepted. It was revoked in Google Cloud on 2026-10-14 21:31:03 UTC; the `effective-fire-132313` project was independently verified `DELETE_REQUESTED`. Earlier assertions in this document that correlation was unproven are superseded **for this named original exposed credential**.

**History caveat:** The secret is still visible in historical Git diffs/commits of the archived portfolio repository; merging a removal PR and archiving a repo do not erase Git history. Revocation mitigates authentication misuse of that specific key. No history rewrite, deletion, de-archive, or claim of historical secret erasure is authorized here. The owner-approved M1 risk acceptance remains part of decision provenance, but the precise key-identity uncertainty for PR #1 is resolved.

## Remaining bounded action
Original portfolio PR #1 has now been correlated exactly to the revoked Cloud key; M1 was previously owner-accepted with explicit residual risk. Preserve historical uncertainty/acceptance chronology and the history exposure caveat; do not restore projects or re-enable billing/Maps APIs for proof.
