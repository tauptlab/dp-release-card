from dp_release_card.card import render_release_card


def test_release_card_shows_public_policy_without_private_fields() -> None:
    release = {
        "query_type": "histogram",
        "values": [1, 2],
        "bin_edges_used": [0, 50, 100],
        "epsilon_spent": 1.0,
        "mechanism": "discrete_laplace",
        "sensitivity": 2.0,
        "proof_scope": "strict_finite_precision",
        "warnings": [],
    }
    receipt = {
        "version": "dp-release-card.receipt.v1",
        "tool_version": "0.1.0",
        "release_digest": "a" * 64,
        "public_policy": {
            "query_type": "histogram",
            "n": 2,
            "column": "age",
            "epsilon": 1.0,
            "bounds": [0, 100],
            "bin_edges": [0, 50, 100],
            "mechanism": "discrete_laplace",
            "sensitivity": 2.0,
            "proof_scope": "strict_finite_precision",
            "strict_finite_precision": True,
        },
        "signature": {"algorithm": "hmac-sha256"},
    }

    card = render_release_card(release=release, receipt=receipt)

    assert "| Column | age |" in card
    assert "| Epsilon | 1.0 |" in card
    assert "| Mechanism | discrete_laplace |" in card
    assert "raw" not in card.lower()
    assert "pre-noise" not in card.lower()


def test_release_card_escapes_markdown_table_cells() -> None:
    release = {
        "query_type": "histogram",
        "values": [1],
        "bin_edges_used": [0, 100],
        "epsilon_spent": 1.0,
        "mechanism": "discrete_laplace",
        "sensitivity": 2.0,
        "proof_scope": "strict_finite_precision",
        "warnings": [],
    }
    receipt = {
        "version": "dp-release-card.receipt.v1",
        "tool_version": "0.1.0",
        "release_digest": "a" * 64,
        "public_policy": {
            "query_type": "histogram",
            "n": 1,
            "column": "age|group",
            "epsilon": 1.0,
            "bounds": [0, 100],
            "bin_edges": [0, 100],
            "mechanism": "discrete_laplace",
            "sensitivity": 2.0,
            "proof_scope": "strict_finite_precision",
            "strict_finite_precision": True,
        },
        "signature": {"algorithm": "hmac-sha256"},
    }

    card = render_release_card(release=release, receipt=receipt)

    assert "| Column | age\\|group |" in card
