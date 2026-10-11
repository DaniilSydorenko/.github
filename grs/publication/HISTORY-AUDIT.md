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

`private-runtime` surfaces are excluded because their intended invariant is “never checked in”; secret/private-content tooling should separately detect accidental commits.
