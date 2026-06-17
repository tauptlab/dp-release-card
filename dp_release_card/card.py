from __future__ import annotations

from pathlib import Path

from .errors import ReleaseCardError


def render_release_card(*, release: dict, receipt: dict) -> str:
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


def _markdown_table_cell(value: object) -> str:
    text = str(value).replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return text.replace("\\", "\\\\").replace("|", "\\|")
