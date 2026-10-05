# GRS validator

GRS v1 starts with a deliberately small deterministic validator.

## Contract

The validator accepts a JSON repository manifest and checks the stable v1 identity fields:

- schema version;
- GRS standard version;
- repository class;
- maturity;
- visibility;
- portfolio flagship/pin-candidate booleans.

This first implementation intentionally does not infer repository quality from ambiguous signals. Additional REQUIRED/WARN/N/A controls should be added only when they can be evaluated with low false-positive risk.

## Usage

```bash
python3 grs/validator.py path/to/repository.json
```

The reusable workflow template in `workflow-templates/grs-governance.yml` demonstrates the intended consumer flow. Repositories should pin third-party actions to immutable commit SHAs.
