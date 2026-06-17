# Roadmap

`dp-release-card` should stay small. The project wins by being easy to inspect,
not by becoming a broad privacy platform.

## Now

- Keep the v1 CSV histogram flow stable.
- Keep runtime dependencies at zero.
- Keep public artifact schemas and examples current.
- Keep CI green across Python 3.10, 3.11, and 3.12.

## Next

- Publish the package through PyPI Trusted Publishing.
- Add a formal schema versioning note for future artifact changes.
- Add a deterministic example-generation helper for docs fixtures.
- Add more small public CSV examples for common histogram use cases.
- Add copy-paste validation snippets for CI users.

## Later

- Consider additional public aggregate release cards if they can be specified
  without exposing production TaupT engine internals.
- Consider machine-readable provenance metadata for public policy inputs.
- Consider optional JSON Schema validation instructions for downstream systems.

## Explicitly Out of Scope

- AutoBound
- AC-PQ
- fairness calibration
- internal planners or routers
- benchmark regime maps
- hosted service workflow code
- private metadata derivation
