# DP Release Card

This card summarizes a verifiable differential-privacy histogram release.

## Release

| Field | Value |
|---|---|
| Query | histogram |
| Mechanism | discrete_laplace |
| Proof scope | strict_finite_precision |
| Epsilon spent | 1.0 |
| Sensitivity | 2.0 |
| Released counts | 2, 3, 4, 2, 1 |
| Bin edges | 0.0, 20.0, 40.0, 60.0, 80.0, 100.0 |

## Public Policy

| Field | Value |
|---|---|
| Column | age |
| Row count | 12 |
| Epsilon | 1.0 |
| Mechanism | discrete_laplace |
| Bounds | [0.0, 100.0] |
| Bin edges | 0.0, 20.0, 40.0, 60.0, 80.0, 100.0 |
| Strict finite precision | True |

## Receipt

| Field | Value |
|---|---|
| Version | dp-release-card.receipt.v1 |
| Tool version | 0.1.0 |
| Release digest | f0d3ab790c42b3a7c2346ff4fd18f0588bf52d0253a33c9a12fe00d3a929bcdd |
| Signature algorithm | hmac-sha256 |

## Warnings

- bounds and bin_edges are caller-attested public metadata; deriving them from private data is outside this tool's DP contract
- negative noisy bin counts are clamped to zero by public post-processing; this costs no additional privacy budget but can add bias
- production TaupT routing, AutoBound, fairness calibration, and service workflow are not included

This project is an open-source demonstration of a release-card workflow. It is
not the production TaupT engine and is not legal or compliance advice.
