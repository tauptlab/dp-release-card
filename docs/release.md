# Release Checklist

This project is not published to PyPI yet. The recommended path is PyPI Trusted
Publishing from GitHub Actions once the package name and repository settings are
finalized.

## Pre-release Checks

Run from the repository root:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m build --sdist --wheel
python -m twine check dist/*
```

Verify the committed example artifacts:

```bash
export DP_RELEASE_CARD_SECRET="example-secret-for-docs"
python -m dp_release_card verify examples/outputs/receipt.json \
  --release examples/outputs/release.json \
  --signing-key-env DP_RELEASE_CARD_SECRET
```

PowerShell:

```powershell
$env:DP_RELEASE_CARD_SECRET="example-secret-for-docs"
python -m dp_release_card verify examples/outputs/receipt.json `
  --release examples/outputs/release.json `
  --signing-key-env DP_RELEASE_CARD_SECRET
```

## Versioning

Before tagging a release:

1. Update `dp_release_card/__init__.py`.
2. Update `pyproject.toml`.
3. Update `CHANGELOG.md`.
4. Regenerate committed example artifacts if the artifact schema or renderer
   changed.
5. Run all pre-release checks.

Use tags like:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Publishing Notes

Do not publish from an unverified local tree. Prefer GitHub Actions with PyPI
Trusted Publishing so no long-lived PyPI token is stored in the repository.

Until Trusted Publishing is configured, keep the project installable from
GitHub:

```bash
python -m pip install "dp-release-card @ git+https://github.com/tauptlab/dp-release-card.git"
```
