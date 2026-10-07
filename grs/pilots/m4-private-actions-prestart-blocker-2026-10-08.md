# M4 private Actions prestart blocker

Canonical evidence: `reports/m4/PRIVATE-ACTIONS-PRESTART-BLOCKER-2026-10-08.md`.

Status: **SYSTEM / CI_INFRA / PRESTART**.

Engineering Labs PR #8 and Engineering Handbook PR #52 are current, mergeable maintenance branches, but their private-repository Actions jobs are failing before any workflow step executes.

Repeated blind retries are paused. Release-green evidence still requires an actual executed workflow.
