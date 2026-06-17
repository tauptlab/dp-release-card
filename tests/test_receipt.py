import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import pytest

from dp_release_card.errors import ReleaseCardError
from dp_release_card.receipt import (
    canonical_json_bytes,
    build_receipt,
    load_json,
    release_digest,
    secret_from_env,
    validate_release_policy_consistency,
    verify_release_digest,
    verify_receipt,
    write_json,
)


def sample_release(**overrides) -> dict:
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
    release.update(overrides)
    return release


def sample_policy(**overrides) -> dict:
    policy = {
        "query_type": "histogram",
        "n": 1,
        "column": "age",
        "epsilon": 1.0,
        "bounds": [0, 100],
        "bin_edges": [0, 50, 100],
        "mechanism": "discrete_laplace",
        "sensitivity": 2.0,
        "proof_scope": "strict_finite_precision",
        "strict_finite_precision": True,
    }
    policy.update(overrides)
    return policy


def test_receipt_sign_and_verify(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    release = sample_release(bin_edges_used=[0, 1, 2])
    policy = sample_policy(n=2, bounds=[0, 2], bin_edges=[0, 1, 2])

    receipt = build_receipt(
        release=release,
        public_policy=policy,
        signing_key_env="DP_RELEASE_CARD_SECRET",
        created_at=datetime(2026, 6, 15, tzinfo=timezone.utc),
    )

    assert receipt["release_digest"] == release_digest(release)
    assert verify_receipt(receipt, signing_key_env="DP_RELEASE_CARD_SECRET")
    assert "raw" not in str(receipt).lower()
    assert "pre_noise" not in str(receipt).lower()


def test_receipt_rejects_tampering(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    receipt = build_receipt(
        release=sample_release(),
        public_policy=sample_policy(),
        signing_key_env="DP_RELEASE_CARD_SECRET",
    )
    receipt["public_policy"]["n"] = 2

    with pytest.raises(ReleaseCardError, match="verification failed"):
        verify_receipt(receipt, signing_key_env="DP_RELEASE_CARD_SECRET")


def test_receipt_rejects_wrong_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    receipt = build_receipt(
        release=sample_release(),
        public_policy=sample_policy(),
        signing_key_env="DP_RELEASE_CARD_SECRET",
    )
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "wrong-secret")

    with pytest.raises(ReleaseCardError, match="verification failed"):
        verify_receipt(receipt, signing_key_env="DP_RELEASE_CARD_SECRET")


def test_receipt_rejects_wrong_key_env_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    monkeypatch.setenv("OTHER_DP_SECRET", "test-secret")
    receipt = build_receipt(
        release=sample_release(),
        public_policy=sample_policy(),
        signing_key_env="DP_RELEASE_CARD_SECRET",
    )

    with pytest.raises(ReleaseCardError, match="does not match"):
        verify_receipt(receipt, signing_key_env="OTHER_DP_SECRET")


def test_verify_release_digest_accepts_matching_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    release = sample_release()
    receipt = build_receipt(
        release=release,
        public_policy=sample_policy(),
        signing_key_env="DP_RELEASE_CARD_SECRET",
    )

    assert verify_release_digest(release, receipt)


def test_verify_release_digest_rejects_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    release = sample_release()
    receipt = build_receipt(
        release=release,
        public_policy=sample_policy(),
        signing_key_env="DP_RELEASE_CARD_SECRET",
    )
    release["values"] = [9, 9]

    with pytest.raises(ReleaseCardError, match="does not match"):
        verify_release_digest(release, receipt)


def test_verify_release_digest_rejects_policy_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    release = sample_release()
    receipt = build_receipt(
        release=release,
        public_policy=sample_policy(),
        signing_key_env="DP_RELEASE_CARD_SECRET",
    )
    receipt["public_policy"]["epsilon"] = 2.0

    with pytest.raises(ReleaseCardError, match="epsilon_spent"):
        verify_release_digest(release, receipt)


def test_release_digest_rejects_non_release_object() -> None:
    with pytest.raises(ReleaseCardError, match="release must be an object"):
        release_digest([])


def test_release_policy_consistency_rejects_malformed_inputs() -> None:
    with pytest.raises(ReleaseCardError, match="release query_type"):
        validate_release_policy_consistency({}, sample_policy())


def test_receipt_builder_rejects_policy_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")

    with pytest.raises(ReleaseCardError, match="epsilon_spent"):
        build_receipt(
            release=sample_release(),
            public_policy=sample_policy(epsilon=2.0),
            signing_key_env="DP_RELEASE_CARD_SECRET",
        )


def test_receipt_builder_rejects_unknown_release_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    release = sample_release(raw_rows=[101])

    with pytest.raises(ReleaseCardError, match="unknown field"):
        build_receipt(
            release=release,
            public_policy=sample_policy(),
            signing_key_env="DP_RELEASE_CARD_SECRET",
        )


@pytest.mark.parametrize(
    "release",
    [
        sample_release(values=[True, 1]),
        sample_release(values=[-1, 1]),
        sample_release(bin_edges_used=[0, 100]),
        sample_release(epsilon_spent=True),
        sample_release(sensitivity=True),
        sample_release(warnings=["ok", 1]),
    ],
)
def test_receipt_builder_rejects_invalid_release_schema(
    monkeypatch: pytest.MonkeyPatch, release: dict
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")

    with pytest.raises(ReleaseCardError):
        build_receipt(
            release=release,
            public_policy=sample_policy(),
            signing_key_env="DP_RELEASE_CARD_SECRET",
        )


def test_receipt_requires_secret_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DP_RELEASE_CARD_SECRET", raising=False)

    with pytest.raises(ReleaseCardError, match="not set"):
        build_receipt(
            release=sample_release(),
            public_policy=sample_policy(),
            signing_key_env="DP_RELEASE_CARD_SECRET",
        )


def test_secret_from_env_rejects_blank_env_name() -> None:
    with pytest.raises(ReleaseCardError, match="name is required"):
        secret_from_env("   ")


def test_secret_from_env_rejects_whitespace_only_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "   ")

    with pytest.raises(ReleaseCardError, match="not set or is empty"):
        secret_from_env("DP_RELEASE_CARD_SECRET")


def test_verify_receipt_rejects_non_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")

    with pytest.raises(ReleaseCardError, match="receipt must be an object"):
        verify_receipt([], signing_key_env="DP_RELEASE_CARD_SECRET")


def test_receipt_builder_rejects_non_object_public_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")

    with pytest.raises(ReleaseCardError, match="public_policy must be an object"):
        build_receipt(
            release=sample_release(),
            public_policy=[],
            signing_key_env="DP_RELEASE_CARD_SECRET",
        )


def test_load_json_rejects_non_utf8(tmp_path) -> None:
    path = tmp_path / "receipt.json"
    path.write_bytes(b"\xff\xfe\x00\x00")

    with pytest.raises(ReleaseCardError, match="not valid UTF-8"):
        load_json(path)


def test_load_json_rejects_duplicate_keys(tmp_path) -> None:
    path = tmp_path / "receipt.json"
    path.write_text('{"version":"bad","version":"also-bad"}', encoding="utf-8")

    with pytest.raises(ReleaseCardError, match="duplicate key"):
        load_json(path)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_load_json_rejects_non_standard_numeric_constants(tmp_path, constant: str) -> None:
    path = tmp_path / "receipt.json"
    path.write_text(f'{{"value": {constant}}}', encoding="utf-8")

    with pytest.raises(ReleaseCardError, match="non-standard numeric constant"):
        load_json(path)


@pytest.mark.parametrize("value", [{"x": float("nan")}, {"x": {1, 2}}])
def test_canonical_json_rejects_non_standard_values(value) -> None:
    with pytest.raises(ReleaseCardError, match="canonical JSON"):
        canonical_json_bytes(value)


def test_write_json_rejects_non_standard_values_without_clobbering(tmp_path) -> None:
    path = tmp_path / "out.json"
    path.write_text("original", encoding="utf-8")

    with pytest.raises(ReleaseCardError, match="JSON serializable"):
        write_json(path, {"x": float("nan")})

    assert path.read_text(encoding="utf-8") == "original"


def test_receipt_builder_rejects_naive_created_at(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")

    with pytest.raises(ReleaseCardError, match="timezone"):
        build_receipt(
            release=sample_release(),
            public_policy=sample_policy(),
            signing_key_env="DP_RELEASE_CARD_SECRET",
            created_at=datetime(2026, 6, 17, 0, 0, 0),
        )


def test_receipt_builder_normalizes_created_at_to_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    receipt = build_receipt(
        release=sample_release(),
        public_policy=sample_policy(),
        signing_key_env="DP_RELEASE_CARD_SECRET",
        created_at=datetime(2026, 6, 17, 9, 0, 0, tzinfo=timezone(timedelta(hours=9))),
    )

    assert receipt["created_at"] == "2026-06-17T00:00:00Z"
    assert verify_receipt(receipt, signing_key_env="DP_RELEASE_CARD_SECRET")


def test_receipt_rejects_signed_malformed_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    payload = {
        "version": "dp-release-card.receipt.v1",
        "tool_version": "0.1.0",
        "created_at": "2026-06-17T00:00:00Z",
        "public_policy": {"n": 1},
    }
    signature = hmac.new(
        b"test-secret",
        canonical_json_bytes(payload),
        hashlib.sha256,
    ).hexdigest()
    receipt = {
        **payload,
        "signature": {
            "algorithm": "hmac-sha256",
            "key_env": "DP_RELEASE_CARD_SECRET",
            "value": signature,
        },
    }

    with pytest.raises(ReleaseCardError, match="release_digest"):
        verify_receipt(receipt, signing_key_env="DP_RELEASE_CARD_SECRET")


def test_receipt_rejects_signed_unknown_top_level_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    payload = {
        "version": "dp-release-card.receipt.v1",
        "tool_version": "0.1.0",
        "created_at": "2026-06-17T00:00:00Z",
        "release_digest": "a" * 64,
        "public_policy": sample_policy(),
        "raw_rows": [101],
    }
    signature = hmac.new(
        b"test-secret",
        canonical_json_bytes(payload),
        hashlib.sha256,
    ).hexdigest()
    receipt = {
        **payload,
        "signature": {
            "algorithm": "hmac-sha256",
            "key_env": "DP_RELEASE_CARD_SECRET",
            "value": signature,
        },
    }

    with pytest.raises(ReleaseCardError, match="unknown field"):
        verify_receipt(receipt, signing_key_env="DP_RELEASE_CARD_SECRET")


def test_receipt_rejects_unknown_public_policy_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    policy = sample_policy(raw_rows=[101])

    with pytest.raises(ReleaseCardError, match="unknown field"):
        build_receipt(
            release=sample_release(),
            public_policy=policy,
            signing_key_env="DP_RELEASE_CARD_SECRET",
        )


@pytest.mark.parametrize(
    "policy",
    [
        sample_policy(n=True),
        sample_policy(column="   "),
        sample_policy(epsilon=True),
        sample_policy(bounds=[False, 100]),
        sample_policy(bin_edges=[0, True, 100]),
        sample_policy(sensitivity=True),
    ],
)
def test_receipt_rejects_boolean_public_policy_numbers(
    monkeypatch: pytest.MonkeyPatch, policy: dict
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")

    with pytest.raises(ReleaseCardError):
        build_receipt(
            release=sample_release(),
            public_policy=policy,
            signing_key_env="DP_RELEASE_CARD_SECRET",
        )


@pytest.mark.parametrize("created_at", ["2026-06-17", "2026-06-17T00:00:00"])
def test_receipt_rejects_timestamp_without_timezone(
    monkeypatch: pytest.MonkeyPatch, created_at: str
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    payload = {
        "version": "dp-release-card.receipt.v1",
        "tool_version": "0.1.0",
        "created_at": created_at,
        "release_digest": "a" * 64,
        "public_policy": {"n": 1},
    }
    signature = hmac.new(
        b"test-secret",
        canonical_json_bytes(payload),
        hashlib.sha256,
    ).hexdigest()
    receipt = {
        **payload,
        "signature": {
            "algorithm": "hmac-sha256",
            "key_env": "DP_RELEASE_CARD_SECRET",
            "value": signature,
        },
    }

    with pytest.raises(ReleaseCardError, match="timezone"):
        verify_receipt(receipt, signing_key_env="DP_RELEASE_CARD_SECRET")
