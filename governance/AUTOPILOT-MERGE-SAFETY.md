# Autopilot Merge Safety Policy

Status: ACTIVE

The canonical machine-readable policy is `governance/autopilot-merge-policy.json`.

The policy is deliberately **default deny**. A merge is never authorized merely because a pull request is mergeable.

## Conditional merge requirements

A bounded merge requires all of the following in the current run:

- explicit authorization covering the current work;
- fresh inspection of the default branch and open pull requests;
- exact-head SHA verification;
- required CI green;
- the pull request is not draft;
- no owner-gated operation is involved;
- no domain-worker ownership conflict exists;
- no collision with another worker's roadmap/surface exists.

## Existing standing Class A/B authorization — how to apply it

The current-run `explicit authorization` requirement is satisfied by the **already granted, bounded** permission in `autopilot-control-plane/AUTHORITY.md` **only for a scheduled worker's own Class A/B PR within its existing repository and domain ownership**. It is not a request for fresh owner approval on every otherwise eligible low-risk PR.

Every individual merge still requires a **fresh current-run** evaluation of authority, exact unchanged head SHA, required successful CI/security checks, non-Draft status, semantic currency, reviews, dependency order, overlap and mergeability. A standing permission is **not** a standing waiver of those checks.

It does **not** transfer to synchronous HQ, owner-authored PRs, another worker's PR, unreviewed product code, Class C changes, changes to security/evidence/public-private semantics, publication, credentials, release, history rewrite, or any unresolved owner/security gate. Domain policy can further restrict or revoke it. On uncertainty, default deny and present one exact owner decision rather than attempting a merge.

This clarifies an existing authorization boundary, **not** mandatory new Governance v1/C01–C07 cross-repository enforcement (owner issue #56 remains separate). No additional merge-policy file, service or scheduled worker is authorized.

## Owner-only operations

The following remain owner-only:

- repository visibility changes;
- destructive history rewrites;
- credential rotation or revocation;
- stable release publication.

## Forbidden automation

Automation must never:

- merge red CI;
- merge after the verified head changed;
- force-update a branch without an expected-SHA lease;
- edit another worker's roadmap;
- silently take over domain product code.

The validator in `grs/validate_autopilot_merge_policy.py` is executed by the GRS Control Plane so these boundaries cannot drift silently.
