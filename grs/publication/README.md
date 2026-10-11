# Publication Boundary Policy

M4 publication manifests make the private→public extraction state machine-readable without changing repository visibility.

The policy separates three questions:

1. What is the target publication architecture?
2. Which repository surfaces still require extraction, sanitization, synthetic replacement, private runtime storage, or review?
3. Have the technical and owner gates actually been satisfied?

A manifest is descriptive governance, not permission to publish.

## Status model

- `inventory-complete` — sensitive-surface inventory exists but extraction may not be scoped.
- `extraction-required` — concrete surfaces remain before the repository can reach the owner gate.
- `ready-for-owner-gate` — current tree, Git history and exact-head CI are all proven safe/green.

`owner_visibility_approval` may be true only in `ready-for-owner-gate`.

## Modes

- `canonical-public` — the repository itself is intended to become the public canonical product.
- `public-code-private-data` — code/platform becomes public while private runtime/data stays physically separate.
- `remain-private` — deliberate private repository.

Visibility changes and history rewrites remain explicit owner-gated operations.
