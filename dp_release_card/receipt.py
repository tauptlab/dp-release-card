from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .errors import ReleaseCardError

RECEIPT_VERSION = "dp-release-card.receipt.v1"
RECEIPT_KEYS = {
    "version",
    "tool_version",
    "created_at",
    "release_digest",
    "public_policy",
    "signature",
}
SIGNATURE_KEYS = {"algorithm", "key_env", "value"}
PUBLIC_POLICY_KEYS = {
    "query_type",
    "n",
    "column",
    "epsilon",
    "bounds",
    "bin_edges",
    "mechanism",
    "sensitivity",
    "proof_scope",
    "strict_finite_precision",
}
RELEASE_KEYS = {
    "query_type",
    "values",
    "bin_edges_used",
    "epsilon_spent",
    "mechanism",
    "sensitivity",
    "proof_scope",
    "warnings",
}


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ReleaseCardError("value is not canonical JSON serializable") from exc


def release_digest(release: dict) -> str:
    validate_release_schema(release)
    return hashlib.sha256(canonical_json_bytes(release)).hexdigest()


def secret_from_env(env_name: str) -> bytes:
    if not env_name or env_name.strip() == "":
        raise ReleaseCardError("signing key environment variable name is required")
    raw = os.environ.get(env_name)
    if not raw or raw.strip() == "":
        raise ReleaseCardError(f"signing key env var {env_name!r} is not set or is empty")
    return raw.encode("utf-8")


def build_receipt(
    *,
    release: dict,
    public_policy: dict,
    signing_key_env: str,
    created_at: datetime | None = None,
) -> dict:
    secret = secret_from_env(signing_key_env)
    validate_release_schema(release)
    validate_public_policy(public_policy)
    validate_release_policy_consistency(release, public_policy)
    created_at = created_at or datetime.now(timezone.utc)
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ReleaseCardError("receipt created_at must include a timezone")
    payload = {
        "version": RECEIPT_VERSION,
        "tool_version": __version__,
        "created_at": created_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "release_digest": release_digest(release),
        "public_policy": public_policy,
    }
    signature = hmac.new(secret, canonical_json_bytes(payload), hashlib.sha256).hexdigest()
    return {
        **payload,
        "signature": {
            "algorithm": "hmac-sha256",
            "key_env": signing_key_env,
            "value": signature,
        },
    }


def verify_receipt(receipt: dict, *, signing_key_env: str) -> bool:
    validate_receipt_schema(receipt, signing_key_env=signing_key_env)
    signature = receipt.get("signature")
    value = signature["value"]

    payload = {k: v for k, v in receipt.items() if k != "signature"}
    secret = secret_from_env(signing_key_env)
    want = hmac.new(secret, canonical_json_bytes(payload), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(value, want):
        raise ReleaseCardError("receipt signature verification failed")
    return True


def verify_release_digest(release: dict, receipt: dict) -> bool:
    if not isinstance(receipt, dict):
        raise ReleaseCardError("receipt must be an object")
    validate_release_schema(release)
    public_policy = receipt.get("public_policy")
    if not isinstance(public_policy, dict):
        raise ReleaseCardError("receipt public_policy must be an object")
    validate_public_policy(public_policy)
    validate_release_policy_consistency(release, public_policy)
    expected = receipt.get("release_digest")
    if not _is_sha256_hex(expected):
        raise ReleaseCardError("receipt release_digest must be a SHA-256 hex digest")
    actual = release_digest(release)
    if not hmac.compare_digest(actual, expected):
        raise ReleaseCardError("release digest does not match receipt")
    return True


def validate_release_policy_consistency(release: dict, policy: dict) -> None:
    validate_release_schema(release)
    validate_public_policy(policy)
    if release["query_type"] != policy["query_type"]:
        raise ReleaseCardError("release query_type does not match public_policy")
    if release["epsilon_spent"] != policy["epsilon"]:
        raise ReleaseCardError("release epsilon_spent does not match public_policy")
    if release["bin_edges_used"] != policy["bin_edges"]:
        raise ReleaseCardError("release bin_edges_used does not match public_policy")
    if policy["bounds"] != [release["bin_edges_used"][0], release["bin_edges_used"][-1]]:
        raise ReleaseCardError("release bin edges do not match public_policy bounds")
    if release["mechanism"] != policy["mechanism"]:
        raise ReleaseCardError("release mechanism does not match public_policy")
    if release["sensitivity"] != policy["sensitivity"]:
        raise ReleaseCardError("release sensitivity does not match public_policy")
    if release["proof_scope"] != policy["proof_scope"]:
        raise ReleaseCardError("release proof_scope does not match public_policy")


def validate_release_schema(release: dict) -> None:
    if not isinstance(release, dict):
        raise ReleaseCardError("release must be an object")
    _reject_unknown_keys("release", release, RELEASE_KEYS)
    if release.get("query_type") != "histogram":
        raise ReleaseCardError("release query_type must be 'histogram'")
    values = release.get("values")
    if (
        not isinstance(values, list)
        or not values
        or any(not _is_non_negative_int(value) for value in values)
    ):
        raise ReleaseCardError("release values must be non-negative integers")
    bin_edges = release.get("bin_edges_used")
    if (
        not isinstance(bin_edges, list)
        or len(bin_edges) != len(values) + 1
        or not all(_is_finite_number(value) for value in bin_edges)
        or any(cur <= prev for prev, cur in zip(bin_edges, bin_edges[1:]))
    ):
        raise ReleaseCardError("release bin_edges_used must match values")
    epsilon = release.get("epsilon_spent")
    if (
        isinstance(epsilon, bool)
        or not isinstance(epsilon, (int, float))
        or not math.isfinite(epsilon)
        or epsilon <= 0
    ):
        raise ReleaseCardError("release epsilon_spent must be positive finite")
    if release.get("mechanism") != "discrete_laplace":
        raise ReleaseCardError("release mechanism must be 'discrete_laplace'")
    sensitivity = release.get("sensitivity")
    if (
        isinstance(sensitivity, bool)
        or not isinstance(sensitivity, (int, float))
        or sensitivity != 2.0
    ):
        raise ReleaseCardError("release sensitivity must be 2.0")
    if release.get("proof_scope") != "strict_finite_precision":
        raise ReleaseCardError("release proof_scope must be 'strict_finite_precision'")
    warnings = release.get("warnings")
    if not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings):
        raise ReleaseCardError("release warnings must be strings")


def validate_receipt_schema(receipt: dict, *, signing_key_env: str) -> None:
    if not isinstance(receipt, dict):
        raise ReleaseCardError("receipt must be an object")
    _reject_unknown_keys("receipt", receipt, RECEIPT_KEYS)
    if receipt.get("version") != RECEIPT_VERSION:
        raise ReleaseCardError(f"receipt version must be {RECEIPT_VERSION!r}")
    if not _is_non_empty_str(receipt.get("tool_version")):
        raise ReleaseCardError("receipt tool_version is missing")
    created_at = receipt.get("created_at")
    if not _is_non_empty_str(created_at):
        raise ReleaseCardError("receipt created_at is missing")
    try:
        parsed_created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReleaseCardError("receipt created_at is not a valid ISO timestamp") from exc
    if parsed_created_at.tzinfo is None or parsed_created_at.utcoffset() is None:
        raise ReleaseCardError("receipt created_at must include a timezone")
    if not _is_sha256_hex(receipt.get("release_digest")):
        raise ReleaseCardError("receipt release_digest must be a SHA-256 hex digest")
    public_policy = receipt.get("public_policy")
    if not isinstance(public_policy, dict):
        raise ReleaseCardError("receipt public_policy must be an object")
    validate_public_policy(public_policy)

    signature = receipt.get("signature")
    if not isinstance(signature, dict):
        raise ReleaseCardError("receipt signature is missing")
    _reject_unknown_keys("receipt signature", signature, SIGNATURE_KEYS)
    if signature.get("algorithm") != "hmac-sha256":
        raise ReleaseCardError("receipt signature algorithm is unsupported")
    if signature.get("key_env") != signing_key_env:
        raise ReleaseCardError("receipt signing key env does not match verifier input")
    if not _is_sha256_hex(signature.get("value")):
        raise ReleaseCardError("receipt signature value must be a SHA-256 hex digest")


def validate_public_policy(policy: dict) -> None:
    if not isinstance(policy, dict):
        raise ReleaseCardError("public_policy must be an object")
    _reject_unknown_keys("public_policy", policy, PUBLIC_POLICY_KEYS)
    if policy.get("query_type") != "histogram":
        raise ReleaseCardError("public_policy query_type must be 'histogram'")
    if (
        not isinstance(policy.get("n"), int)
        or isinstance(policy.get("n"), bool)
        or policy["n"] <= 0
    ):
        raise ReleaseCardError("public_policy n must be a positive integer")
    if not _is_non_empty_str(policy.get("column")):
        raise ReleaseCardError("public_policy column is missing")
    epsilon = policy.get("epsilon")
    if (
        isinstance(epsilon, bool)
        or not isinstance(epsilon, (int, float))
        or not math.isfinite(epsilon)
        or epsilon <= 0
    ):
        raise ReleaseCardError("public_policy epsilon must be positive finite")
    bounds = policy.get("bounds")
    if (
        not isinstance(bounds, list)
        or len(bounds) != 2
        or not all(_is_finite_number(value) for value in bounds)
        or bounds[1] <= bounds[0]
    ):
        raise ReleaseCardError("public_policy bounds must be [lower, upper]")
    bin_edges = policy.get("bin_edges")
    if (
        not isinstance(bin_edges, list)
        or len(bin_edges) < 2
        or not all(_is_finite_number(value) for value in bin_edges)
        or any(cur <= prev for prev, cur in zip(bin_edges, bin_edges[1:]))
        or bin_edges[0] != bounds[0]
        or bin_edges[-1] != bounds[1]
    ):
        raise ReleaseCardError("public_policy bin_edges must be strictly increasing bounds")
    if policy.get("mechanism") != "discrete_laplace":
        raise ReleaseCardError("public_policy mechanism must be 'discrete_laplace'")
    sensitivity = policy.get("sensitivity")
    if (
        isinstance(sensitivity, bool)
        or not isinstance(sensitivity, (int, float))
        or sensitivity != 2.0
    ):
        raise ReleaseCardError("public_policy sensitivity must be 2.0")
    if policy.get("proof_scope") != "strict_finite_precision":
        raise ReleaseCardError("public_policy proof_scope must be 'strict_finite_precision'")
    if policy.get("strict_finite_precision") is not True:
        raise ReleaseCardError("public_policy strict_finite_precision must be true")


def _reject_unknown_keys(label: str, value: dict, allowed: set[str]) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        names = ", ".join(repr(name) for name in unknown)
        raise ReleaseCardError(f"{label} contains unknown field(s): {names}")


def _is_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _is_non_negative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_non_empty_str(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_sha256_hex(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdefABCDEF" for char in value)


def load_json(path: str | Path) -> dict:
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as f:
            value = json.load(
                f,
                object_pairs_hook=_reject_duplicate_object_pairs,
                parse_constant=_reject_json_constant,
            )
    except OSError as exc:
        raise ReleaseCardError(f"cannot read JSON: {path}: {exc}") from exc
    except UnicodeError as exc:
        raise ReleaseCardError(f"JSON is not valid UTF-8: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseCardError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ReleaseCardError(f"JSON document must be an object: {path}")
    return value


def _reject_duplicate_object_pairs(pairs: list[tuple[str, Any]]) -> dict:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ReleaseCardError(f"JSON object contains duplicate key: {key!r}")
        out[key] = value
    return out


def _reject_json_constant(value: str) -> None:
    raise ReleaseCardError(f"JSON contains non-standard numeric constant: {value}")


def write_json(path: str | Path, value: dict) -> None:
    path = Path(path)
    try:
        text = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise ReleaseCardError(f"cannot write JSON: {path}: {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise ReleaseCardError(f"value is not JSON serializable: {path}") from exc
