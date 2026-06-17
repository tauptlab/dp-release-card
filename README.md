# dp-release-card

Generate a verifiable differential-privacy release card from a CSV histogram.

This project is intentionally small. It shows the public workflow:

```text
CSV + caller-attested public policy -> DP release JSON -> signed receipt -> Markdown card
```

It does **not** include the production TaupT engine, AutoBound, AC-PQ, fairness
calibration, internal routing, benchmark regime maps, or service workflow.

## Quickstart

PowerShell:

```powershell
python -m pip install -e ".[test]"

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
python -m pip install -e ".[test]"

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

If your Python environment does not put console scripts on PATH, use
`python -m dp_release_card ...` with the same arguments.

## Inputs

- A UTF-8 CSV file with a header row.
- A numeric column name.
- Public lower/upper bounds.
- Public histogram bin edges.
- A positive epsilon.
- `--strict`, which selects the v1 finite-precision `discrete_laplace` path.
- A signing secret supplied by environment variable name, never directly on the command line.

CSV header names must be unique and non-blank. Each data row must have exactly
the same number of fields as the header row; blank rows, missing fields, and
extra fields are rejected instead of being silently repaired. The selected
column must be non-blank, numeric, and finite in every data row.

`bounds` and `bin_edges` are caller-attested public metadata. Deriving them from
private data is outside this tool's DP contract.

## Outputs

- `release.json`: noisy counts plus DP metadata.
- `receipt.json`: canonical release digest, public policy, and HMAC-SHA256 signature.
- `release-card.md`: a human-readable summary.

The public release and receipt do not include raw rows, raw column samples,
private pre-noise histogram counts, or input file hashes.

`dp-release-card verify receipt.json` verifies the receipt signature and public
policy. Add `--release release.json` to also verify that a release file matches
the receipt digest and the signed public policy metadata.

## Scope

The v1 histogram uses fixed-size bounded replace-one dense histogram sensitivity
`2`. Values are clamped to public bounds and assigned to public bins before
noise is added. Negative noisy bin counts are clamped to zero as public
post-processing; this costs no additional privacy budget but can add bias.

This is an open-source demonstration of a verifiable release-card workflow. It
is not legal or compliance advice.

## Development

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```
