# .github
    GitHub governance, repository standards, reusable workflows, and profile-wide automation.

## Autopilot stability governance

Scheduled Autopilot work in this repository follows the canonical [Control Plane stability-first repair contract](https://github.com/DaniilSydorenko/autopilot-control-plane/blob/main/CONTROL_PLANE.md#stability-first-repair-contract-2026-10-11). Classify failures by source, prove root causes, use bounded retries, verify real scheduled cycles, and stop unnecessary self-maintenance. Repository-local security, product, provenance and approval requirements still apply; the stricter rule wins. The canonical contract is maintained only in the Control Plane, not copied here.
