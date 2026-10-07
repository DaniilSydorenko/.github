# M4 — Release-gate and licensing plan

Date: 2026-10-07
Status: **PREPARED — no visibility or license decision applied**

## Purpose

Convert the M4 public-safety audit into concrete release gates for the repositories that may eventually become public.

This is a central governance plan only. It does not modify consumer repositories and does not grant publication authority.

## Engineering Labs

### Current target

Preferred publication model: **full repository**, after owning-lane release gates are green and the owner approves visibility.

### Required release gates

1. Public-safe README/status remains current.
2. Explicit license decision is recorded and applied.
3. Repository-local GRS manifest and consumer workflow are present.
4. PR template and issue taxonomy are present.
5. CONTRIBUTING.md and SECURITY.md are present.
6. Quality workflow executes real steps and passes.
7. Full-history secret scan executes real steps and passes.
8. No employer-confidential or non-synthetic material is present.
9. Repository metadata is prepared.
10. Owner explicitly approves private → public visibility change.

### Licensing recommendation

For a code-first engineering-learning repository, **MIT** is the simplest default candidate because it is familiar, permissive, and easy for recruiters/OSS users to understand.

This is a recommendation only. The owner must explicitly choose the license before publication.

## Engineering Handbook

### Current target

Preferred publication model: **sanitized/public projection first** unless the personalized surfaces are separated or proven safe.

### Public-boundary result

The dedicated personalized area contains career-specific evidence/gap/knowledge/learning maps. That content is useful to the private system but should not be assumed public simply because the technical handbook itself is public-suitable.

Automation and operating-system material is not automatically unsafe, but publication should be deliberate because it describes internal control processes and long-lived personal planning.

### Required release gates

1. Decide whether publication is:
   - full repository after sanitization; or
   - separate sanitized/public projection.
2. Separate or exclude personalized career-context material from the public artifact unless explicitly approved.
3. Explicit licensing decision.
4. Repository-local GRS knowledge consumer.
5. PR template and issue taxonomy.
6. CONTRIBUTING.md and SECURITY.md.
7. Handbook validation executes real steps and passes.
8. Secret scan executes real steps and passes.
9. Generated release artifacts, if included, are checked for accidental private content.
10. Metadata/public README are prepared.
11. Owner explicitly approves the final publication model and visibility.

### Licensing recommendation

Because the Handbook is primarily authored knowledge/content with executable examples, a clean candidate model is:

- documentation/content: **CC BY 4.0**;
- code/examples/scripts: **MIT**.

That dual-license model is only a recommendation. A single MIT license for the whole repository is simpler but is less explicit about reuse expectations for prose. The owner should choose deliberately.

## Career Intelligence

### Current target

**Keep canonical repository private.**

The public website/API projection is the default public artifact.

No repository-level license recommendation is needed for M4 unless the owner later chooses a public source artifact. Licensing the canonical private repository is not a prerequisite for the current public projection strategy.

If a separate sanitized public-source artifact is later created, its license should be chosen for that artifact after its exact contents are known.

## CI interpretation

For Labs and Handbook, recent maintenance branches have shown zero-step/prestart failures in private-repository Actions.

Those results are **SYSTEM/CI_INFRA/PRESTART**, not code failures and not release-green evidence.

M4 release readiness requires at least one fresh execution in which the relevant quality/validation and secret-scan jobs actually run their steps and complete successfully.

No gate may be weakened merely to produce a green badge.

## Owner decisions

The minimum future owner decisions remain:

1. Engineering Labs: approve publication timing and license after gates are green.
2. Engineering Handbook: choose full repo after sanitization vs sanitized projection, then choose licensing model.
3. Career Intelligence: confirm canonical repo remains private or explicitly request a separate public-source design.

Until those decisions are made, automation should continue preparing evidence and owning-lane remediation without changing visibility.
