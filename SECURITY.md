# Security Policy

`dp-release-card` is a small open-source demonstration of verifiable public
release artifacts. It is not legal, compliance, or deployment advice.

## Supported Versions

| Version | Supported |
|---|---|
| 0.1.x | Yes |

## Reporting Security Issues

Please do not open public issues for suspected vulnerabilities involving
signature handling, artifact tampering, private data exposure, or privacy
contract bypasses.

Report issues privately to the project maintainers through the GitHub security
advisory flow for this repository.

## Security Scope

In scope:

- receipt signature verification bugs,
- release digest mismatch bugs,
- public artifact leakage of raw/private fields,
- output overwrite or partial-write hazards,
- parsing behavior that bypasses documented validation.

Out of scope:

- claims about the private TaupT production engine,
- legal or regulatory compliance conclusions,
- private metadata derivation outside this tool,
- misuse with non-public bounds or bin edges.
