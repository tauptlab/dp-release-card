from __future__ import annotations

from pathlib import Path

from .errors import ReleaseCardError
from .receipt import RECEIPT_VERSION, verify_release_digest


def render_release_card(*, release: dict, receipt: dict) -> str:
    _validate_card_inputs(release=release, receipt=receipt)
    policy = receipt["public_policy"]
    warnings = release.get("warnings", [])
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) if warnings else "- None"
    values = _markdown_table_cell(", ".join(str(v) for v in release["values"]))
    bins = _markdown_table_cell(", ".join(str(v) for v in release["bin_edges_used"]))
    column = _markdown_table_cell(policy["column"])
    return f"""# DP Release Card

This card summarizes a verifiable differential-privacy histogram release.

## Release

| Field | Value |
|---|---|
| Query | {release["query_type"]} |
| Mechanism | {release["mechanism"]} |
| Proof scope | {release["proof_scope"]} |
| Epsilon spent | {release["epsilon_spent"]} |
| Sensitivity | {release["sensitivity"]} |
| Released counts | {values} |
| Bin edges | {bins} |

## Public Policy

| Field | Value |
|---|---|
| Column | {column} |
| Row count | {policy["n"]} |
| Epsilon | {policy["epsilon"]} |
| Mechanism | {policy["mechanism"]} |
| Bounds | [{policy["bounds"][0]}, {policy["bounds"][1]}] |
| Bin edges | {bins} |
| Strict finite precision | {policy["strict_finite_precision"]} |

## Receipt

| Field | Value |
|---|---|
| Version | {receipt["version"]} |
| Tool version | {receipt["tool_version"]} |
| Release digest | {receipt["release_digest"]} |
| Signature algorithm | {receipt["signature"]["algorithm"]} |

## Warnings

{warning_lines}

This project is an open-source demonstration of a release-card workflow. It is
not the production TaupT engine and is not legal or compliance advice.
"""


def write_card(path: str | Path, *, release: dict, receipt: dict) -> None:
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_release_card(release=release, receipt=receipt), encoding="utf-8")
    except OSError as exc:
        raise ReleaseCardError(f"cannot write release card: {path}: {exc}") from exc


def _validate_card_inputs(*, release: dict, receipt: dict) -> None:
    if not isinstance(receipt, dict):
        raise ReleaseCardError("receipt must be an object")
    if receipt.get("version") != RECEIPT_VERSION:
        raise ReleaseCardError(f"receipt version must be {RECEIPT_VERSION!r}")
    if not _is_non_empty_str(receipt.get("tool_version")):
        raise ReleaseCardError("receipt tool_version is missing")
    if not _is_sha256_hex(receipt.get("release_digest")):
        raise ReleaseCardError("receipt release_digest must be a SHA-256 hex digest")
    signature = receipt.get("signature")
    if not isinstance(signature, dict):
        raise ReleaseCardError("receipt signature is missing")
    if signature.get("algorithm") != "hmac-sha256":
        raise ReleaseCardError("receipt signature algorithm is unsupported")
    if not _is_non_empty_str(signature.get("key_env")):
        raise ReleaseCardError("receipt signature key_env is missing")
    if not _is_sha256_hex(signature.get("value")):
        raise ReleaseCardError("receipt signature value must be a SHA-256 hex digest")
    policy = receipt.get("public_policy")
    if not isinstance(policy, dict):
        raise ReleaseCardError("receipt public_policy must be an object")
    verify_release_digest(release, receipt)


def _markdown_table_cell(value: object) -> str:
    text = str(value).replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return text.replace("\\", "\\\\").replace("|", "\\|")


def _is_non_empty_str(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_sha256_hex(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdefABCDEF" for char in value)
