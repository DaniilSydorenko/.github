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
