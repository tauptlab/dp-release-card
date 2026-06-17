# Artifact Schemas

`dp-release-card` produces two machine-readable JSON artifacts and one Markdown
card. The JSON schemas in this repository document the public shape of the v1
artifacts:

- [release.schema.json](../schema/release.schema.json)
- [receipt.schema.json](../schema/receipt.schema.json)

The schemas intentionally describe public artifact structure. The Python
implementation enforces additional cross-field checks that JSON Schema cannot
fully express on its own:

- `bin_edges_used` has exactly one more item than `values`.
- receipt `release_digest` is the canonical SHA-256 digest of `release.json`.
- receipt `public_policy` is consistent with the release metadata.
- receipt signatures are verified with HMAC-SHA256 and the named environment
  variable.
- public bounds and bin edges are finite and strictly increasing.

## Release JSON

`release.json` is the public DP result. It does not include raw rows, raw column
samples, private pre-noise counts, input file hashes, or signing secrets.

Required fields:

| Field | Meaning |
|---|---|
| `query_type` | Always `histogram` in v1. |
| `values` | Noisy, non-negative integer bin counts after public post-processing. |
| `bin_edges_used` | Public bin edges used for the release. |
| `epsilon_spent` | Positive finite epsilon spent on this release. |
| `mechanism` | Always `discrete_laplace` in v1. |
| `sensitivity` | Always `2.0` in v1. |
| `proof_scope` | Always `strict_finite_precision` in v1. |
| `warnings` | Human-readable caveats for the public artifact. |

## Receipt JSON

`receipt.json` is a signed public policy and release digest. It lets another
party verify that a release file still matches the signed artifact.

Required fields:

| Field | Meaning |
|---|---|
| `version` | Receipt schema version. |
| `tool_version` | `dp-release-card` version that created the receipt. |
| `created_at` | UTC timestamp. |
| `release_digest` | Canonical SHA-256 digest of `release.json`. |
| `public_policy` | Public policy metadata, including `n`, column, bounds, bins, epsilon, mechanism, and proof scope. |
| `signature` | HMAC-SHA256 metadata and signature value. |

## Example Artifacts

See [examples/outputs](../examples/outputs) for a committed artifact snapshot:

- [release.json](../examples/outputs/release.json)
- [receipt.json](../examples/outputs/receipt.json)
- [release-card.md](../examples/outputs/release-card.md)

The example receipt uses the demo secret `example-secret-for-docs` and is for
documentation only.
