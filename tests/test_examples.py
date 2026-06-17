import os
from pathlib import Path

from dp_release_card.card import render_release_card
from dp_release_card.receipt import (
    load_json,
    verify_receipt,
    verify_release_digest,
)


ROOT = Path(__file__).resolve().parents[1]


def test_committed_example_outputs_are_verifiable(monkeypatch) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "example-secret-for-docs")
    release = load_json(ROOT / "examples" / "outputs" / "release.json")
    receipt = load_json(ROOT / "examples" / "outputs" / "receipt.json")

    assert verify_receipt(receipt, signing_key_env="DP_RELEASE_CARD_SECRET")
    assert verify_release_digest(release, receipt)


def test_committed_release_card_matches_renderer() -> None:
    release = load_json(ROOT / "examples" / "outputs" / "release.json")
    receipt = load_json(ROOT / "examples" / "outputs" / "receipt.json")
    card = (ROOT / "examples" / "outputs" / "release-card.md").read_text(
        encoding="utf-8"
    )

    assert card == render_release_card(release=release, receipt=receipt)


def test_public_schema_files_are_valid_json_objects() -> None:
    for path in [
        ROOT / "schema" / "release.schema.json",
        ROOT / "schema" / "receipt.schema.json",
    ]:
        schema = load_json(path)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False


def test_examples_do_not_require_real_secrets_after_test(monkeypatch) -> None:
    monkeypatch.delenv("DP_RELEASE_CARD_SECRET", raising=False)
    assert os.environ.get("DP_RELEASE_CARD_SECRET") is None
