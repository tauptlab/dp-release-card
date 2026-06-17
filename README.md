# dp-release-card

[![CI](https://github.com/tauptlab/dp-release-card/actions/workflows/ci.yml/badge.svg)](https://github.com/tauptlab/dp-release-card/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Generate a verifiable differential-privacy release card from a CSV histogram.

`dp-release-card` is a small, dependency-free Python CLI that turns a numeric
CSV column and caller-attested public policy into three artifacts:

```text
CSV + public bounds/bins -> DP release JSON -> signed receipt -> Markdown card
```

It is designed as a clean, auditable open-source slice of a release workflow,
not as a full privacy platform.

## What This Project Includes

- A strict v1 CSV histogram release flow.
- Public bounds and public bin edges supplied by the caller.
- Bounded replace-one dense histogram sensitivity fixed at `2`.
- Finite-precision `discrete_laplace` noise.
- HMAC-SHA256 receipts signed with a secret from an environment variable.
- Receipt verification, with optional release digest verification.
- A human-readable Markdown release card.
- Tests for parsing, validation, tamper detection, output safety, and CLI flows.

## What This Project Does Not Include

This repository intentionally does **not** include the production TaupT engine,
AutoBound, AC-PQ, fairness calibration, internal planners/routers, benchmark
regime maps, service workflow code, or any private metadata derivation.

If you derive bounds or bin edges from private data, that step is outside this
tool's DP contract. In v1, bounds and bins must be public metadata.

## Installation

From a clone, recommended for the quickstart because it includes
`examples/ages.csv`:

```bash
git clone https://github.com/tauptlab/dp-release-card.git
cd dp-release-card
python -m pip install -e ".[test]"
```

From GitHub without cloning, if you already have your own CSV:

```bash
python -m pip install "dp-release-card @ git+https://github.com/tauptlab/dp-release-card.git"
```

If your Python environment does not put console scripts on `PATH`, use
`python -m dp_release_card ...` with the same arguments shown below.

## Quickstart

PowerShell:

```powershell
$env:DP_RELEASE_CARD_SECRET="dev-secret-at-least-for-local-demo"

dp-release-card histogram examples/ages.csv `
  --column age `
  --epsilon 1.0 `
  --bounds 0,100 `
  --bins 0,20,40,60,80,100 `
  --strict `
  --out release.json `
  --receipt receipt.json `
  --card release-card.md `
  --signing-key-env DP_RELEASE_CARD_SECRET

dp-release-card verify receipt.json --signing-key-env DP_RELEASE_CARD_SECRET

dp-release-card verify receipt.json `
  --release release.json `
  --signing-key-env DP_RELEASE_CARD_SECRET
```

macOS/Linux:

```bash
export DP_RELEASE_CARD_SECRET="dev-secret-at-least-for-local-demo"

dp-release-card histogram examples/ages.csv \
  --column age \
  --epsilon 1.0 \
  --bounds 0,100 \
  --bins 0,20,40,60,80,100 \
  --strict \
  --out release.json \
  --receipt receipt.json \
  --card release-card.md \
  --signing-key-env DP_RELEASE_CARD_SECRET

dp-release-card verify receipt.json --signing-key-env DP_RELEASE_CARD_SECRET

dp-release-card verify receipt.json \
  --release release.json \
  --signing-key-env DP_RELEASE_CARD_SECRET
```

The `verify` command checks the receipt signature and signed public policy.
Passing `--release release.json` also checks that the release file matches the
receipt digest.

## CLI Reference

### `histogram`

```bash
dp-release-card histogram INPUT.csv \
  --column COLUMN \
  --epsilon EPSILON \
  --bounds LOWER,UPPER \
  --bins EDGE0,EDGE1,...,EDGEN \
  --strict \
  --out release.json \
  --receipt receipt.json \
  --card release-card.md \
  --signing-key-env ENV_NAME
```

| Argument | Meaning |
|---|---|
| `INPUT.csv` | UTF-8 CSV file with a header row. |
| `--column` | Numeric column to release. |
| `--epsilon` | Positive finite privacy epsilon. |
| `--bounds` | Public lower and upper clamp bounds. |
| `--bins` | Public, strictly increasing bin edges. Must start/end at bounds. |
| `--strict` | Required in v1. Selects the finite-precision `discrete_laplace` path. |
| `--out` | Release JSON output path. |
| `--receipt` | Signed receipt JSON output path. |
| `--card` | Markdown release-card output path. |
| `--signing-key-env` | Name of the environment variable holding the HMAC secret. |

### `verify`

```bash
dp-release-card verify receipt.json \
  --signing-key-env ENV_NAME

dp-release-card verify receipt.json \
  --release release.json \
  --signing-key-env ENV_NAME
```

## Input Contract

The CSV reader is intentionally strict:

- The file must be UTF-8, optionally with a UTF-8 BOM.
- A header row is required.
- Header names must be unique and non-blank.
- Each data row must have exactly the same number of fields as the header.
- Blank rows, missing fields, and extra fields are rejected.
- The selected column must be non-blank, numeric, and finite in every data row.

The release flow also requires:

- `epsilon > 0`.
- finite `bounds` with upper > lower.
- finite, strictly increasing `bins`.
- `bins[0] == bounds[0]` and `bins[-1] == bounds[1]`.
- `--strict`.
- a non-empty signing secret available through `--signing-key-env`.

## Output Contract

`release.json` contains only the public release:

```json
{
  "query_type": "histogram",
  "values": [1, 2, 3],
  "bin_edges_used": [0.0, 20.0, 40.0, 60.0],
  "epsilon_spent": 1.0,
  "mechanism": "discrete_laplace",
  "sensitivity": 2.0,
  "proof_scope": "strict_finite_precision",
  "warnings": []
}
```

`receipt.json` contains:

- a canonical release digest,
- public policy metadata,
- tool version,
- UTC timestamp,
- HMAC-SHA256 signature metadata.

`release-card.md` is a Markdown summary intended for humans.

The public release and receipt do **not** include raw rows, raw column samples,
private pre-noise histogram counts, input file hashes, or signing secrets.

## Privacy Model

The v1 histogram uses a fixed-size bounded replace-one dense histogram model:

- Values are clamped to public bounds.
- Values are assigned to public bin edges.
- Sensitivity is fixed at `2`.
- Noise is sampled with the finite-precision `discrete_laplace` mechanism.
- Negative noisy bin counts are clamped to zero as public post-processing.

Clamping negative noisy counts costs no additional privacy budget, but it can
add bias. This project is not legal, compliance, or deployment advice.

## Security Notes

- Signing secrets are never accepted directly as CLI values.
- `--signing-key-env` names the environment variable that contains the secret.
- Receipt verification requires the same environment variable name and secret.
- `verify receipt.json` authenticates the receipt payload.
- `verify receipt.json --release release.json` also authenticates the release
  file against the signed digest and public policy.

## Development

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

The CI matrix runs tests on Python 3.10, 3.11, and 3.12.

## Project Status

This is a focused v0.1 implementation. The public API and JSON schema are kept
small on purpose and may change before a 1.0 release.

Planned directions should stay within the public-slice boundary: better docs,
more examples, clearer schema references, and stronger packaging polish. The
private TaupT production engine remains out of scope.

## License

MIT. See [LICENSE](LICENSE).
