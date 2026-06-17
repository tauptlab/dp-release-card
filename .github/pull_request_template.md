## Summary

-

## Verification

- [ ] `python -m pytest -q`
- [ ] `python -m build --sdist --wheel`
- [ ] `python -m twine check dist/*`

## Boundary Check

- [ ] This change does not add production TaupT engine internals.
- [ ] This change does not expose raw private rows, raw samples, pre-noise counts, input file hashes, or signing secrets.
- [ ] Artifact contract changes are reflected in README/docs/schema/changelog.
