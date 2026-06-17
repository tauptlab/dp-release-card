# Contributing

Thanks for taking a look at `dp-release-card`.

The project is intentionally small. Contributions are welcome when they keep
the public-slice boundary clear and do not pull in production TaupT engine
internals.

## Local Setup

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

## Contribution Guidelines

- Keep runtime dependencies at zero unless there is a strong reason to add one.
- Keep v1 focused on public-policy CSV histogram releases.
- Do not add AutoBound, AC-PQ, fairness calibration, planner/router logic,
  internal benchmark maps, or service workflow code.
- Add tests for validation, artifact shape, CLI behavior, and tamper handling.
- Update `README.md`, `docs/schema.md`, and `CHANGELOG.md` when artifact
  contracts change.
- Do not include raw private rows, raw samples, pre-noise counts, input file
  hashes, or signing secrets in public artifacts by default.

## Pull Request Checklist

- [ ] Tests pass with `python -m pytest -q`.
- [ ] Public artifact fields are documented.
- [ ] New output files do not expose private data.
- [ ] README examples still match the CLI.
- [ ] Changes stay inside the open-source boundary.
