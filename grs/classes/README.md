# GRS v1 Repository Class Profiles

These profiles define the default applicability level for GRS controls. Repository manifests select a class; they do not copy these policies.

| Control | profile | oss-library | product | engineering-labs | knowledge | platform | historical |
|---|---|---|---|---|---|---|---|
| README/status | REQUIRED | REQUIRED | REQUIRED | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| repository metadata | REQUIRED | REQUIRED | REQUIRED | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| .gitignore | REQUIRED | REQUIRED | REQUIRED | REQUIRED | REQUIRED | REQUIRED | RECOMMENDED |
| licensing decision | N/A | REQUIRED | REQUIRED | REQUIRED | REQUIRED before public | REQUIRED | REQUIRED if historically licensed |
| secret hygiene | REQUIRED | REQUIRED | REQUIRED | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| PR template | OPTIONAL | REQUIRED | REQUIRED | REQUIRED | RECOMMENDED | REQUIRED | N/A |
| issue taxonomy | N/A | REQUIRED | REQUIRED | REQUIRED | RECOMMENDED | REQUIRED | N/A |
| tests | N/A | REQUIRED | REQUIRED | REQUIRED | validation-specific | REQUIRED | N/A |
| lint/typecheck | N/A | REQUIRED when applicable | REQUIRED when applicable | REQUIRED when applicable | validation-specific | REQUIRED when applicable | N/A |
| SECURITY.md | N/A | REQUIRED | RECOMMENDED | RECOMMENDED | OPTIONAL | RECOMMENDED | OPTIONAL |
| CONTRIBUTING.md | N/A | REQUIRED | RECOMMENDED | RECOMMENDED | RECOMMENDED | RECOMMENDED | N/A |
| ADR/design decisions | N/A | RECOMMENDED | REQUIRED for flagship | REQUIRED | RECOMMENDED | REQUIRED for flagship | N/A |
| release discipline | N/A | REQUIRED | when releasable | milestone-based | generated-doc releases if used | when releasable | N/A |
| branch governance | RECOMMENDED | REQUIRED | REQUIRED for public flagship | RECOMMENDED | RECOMMENDED | REQUIRED for flagship | N/A |

## Interpretation rules

- `REQUIRED` is enforceable and produces FAIL when deterministically violated.
- `RECOMMENDED` produces WARN.
- `OPTIONAL` is informational.
- `N/A` is intentionally excluded from evaluation.
- Conditional entries become REQUIRED only when their condition is true.
- Security controls may not be weakened by repository-local overrides merely to obtain PASS.
- `historical` deliberately avoids modernization theater: safety, truthful status, and preserved evidence matter more than contemporary project cosmetics.

## v1 control families

The validator should initially implement deterministic checks with low false-positive risk:

1. manifest/schema validity;
2. README/status presence;
3. repository metadata consistency where observable;
4. required governance/community files;
5. obvious generated-artifact and secret-hygiene policy surfaces;
6. class-appropriate engineering workflow presence.

More invasive or ambiguous checks remain advisory until their signal quality is proven.
