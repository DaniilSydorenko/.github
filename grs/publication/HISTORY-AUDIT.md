# History path audit

`audit_history_paths.py` is a read-only M4 pre-publication helper.

It checks the complete reachable Git history for paths declared sensitive by a publication-boundary manifest. It intentionally does **not** inspect or rewrite content and never changes refs.

Example:

```bash
python3 grs/publication/audit_history_paths.py \
  ../engineering-handbook \
  grs/publication/engineering-handbook.publication.json
```

Exit codes:

- `0` — no declared history-audited path exists in reachable history;
- `1` — invalid input/tooling failure;
- `2` — historical sensitive-path match; review is required.

A `2` is not authorization to rewrite history. Any filter/rewrite/force update remains an explicit owner gate. The tool is a detector, not a mutator.

`private-runtime` surfaces are **included** in the historical-path audit. They are intended never to be committed, so a historical match requires review before any publication decision. Hidden paths such as `.local/` must remain distinct from non-hidden `local/`. This path-only check does not prove absence of sensitive contents in other files; full-history secret/private-content review and owner publication authorization remain independent gates.


## Current-tree snapshot audit (independent, read-only)

The companion `audit_current_tree.py` checks **tracked paths on one explicit GitHub tree SHA**, without requiring access to sensitive file contents. Export the REST `git/trees/<branch>?recursive=1` JSON response with an account authorized to read the target repository, then execute:

```bash
python3 grs/publication/audit_current_tree.py \
  ./tree-snapshot.json \
  grs/publication/career-intelligence.publication.json
```

It fails closed on a truncated/invalid tree or malformed path declarations. JSON output includes the checked Git tree SHA, per-manifest-surface counts and `publication_authorized: false`. Exit codes: **0** no declared current-tree path match, **1** invalid/insufficient snapshot, **2** declared path matches and needs review.

**Important:** A 0 only confirms absence of *declared paths in the provided one-SHA tree*. It does not inspect file contents, historical refs, off-manifest secrets, deployment, or certify publication readiness. Run the separate full-history and content/secret audits and retain the owner publication gate. GitHub's `truncated: true` must never be accepted as a clean result.
