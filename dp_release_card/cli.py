from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Callable

from .card import write_card
from .csvio import read_numeric_column
from .errors import ReleaseCardError
from .histogram import (
    HISTOGRAM_SENSITIVITY,
    MECHANISM,
    PROOF_SCOPE,
    parse_float_list,
    release_histogram,
    validate_histogram_policy,
)
from .receipt import (
    build_receipt,
    load_json,
    secret_from_env,
    verify_receipt,
    verify_release_digest,
    write_json,
)

DASH_VALUE_OPTIONS = {"--bounds", "--bins"}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parse_argv = sys.argv[1:] if argv is None else argv
    try:
        args = parser.parse_args(_normalize_dash_value_options(parse_argv))
        if args.command == "histogram":
            return _cmd_histogram(args)
        if args.command == "verify":
            return _cmd_verify(args)
        parser.error("missing command")
    except ReleaseCardError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        return _system_exit_code(exc)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dp-release-card",
        description="Generate verifiable DP release cards for public-policy CSV histograms.",
    )
    sub = parser.add_subparsers(dest="command")

    hist = sub.add_parser("histogram", help="release a strict finite-precision DP histogram")
    hist.add_argument("input", help="input CSV path")
    hist.add_argument("--column", required=True, help="numeric CSV column to release")
    hist.add_argument("--epsilon", required=True, type=float, help="privacy epsilon")
    hist.add_argument("--bounds", required=True, help="public lower,upper bounds, e.g. 0,100")
    hist.add_argument("--bins", required=True, help="public bin edges, e.g. 0,20,40,60,80,100")
    hist.add_argument("--strict", action="store_true", help="require strict discrete_laplace path")
    hist.add_argument("--out", required=True, help="release JSON output path")
    hist.add_argument("--receipt", required=True, help="signed receipt JSON output path")
    hist.add_argument("--card", required=True, help="Markdown release card output path")
    hist.add_argument(
        "--signing-key-env",
        required=True,
        help="environment variable holding the HMAC signing secret",
    )

    verify = sub.add_parser("verify", help="verify a signed receipt")
    verify.add_argument("receipt", help="receipt JSON path")
    verify.add_argument(
        "--release",
        help="optional release JSON path to compare against the receipt digest",
    )
    verify.add_argument(
        "--signing-key-env",
        required=True,
        help="environment variable holding the HMAC signing secret",
    )
    return parser


def _normalize_dash_value_options(argv: list[str]) -> list[str]:
    normalized: list[str] = []
    index = 0
    while index < len(argv):
        item = argv[index]
        if item in DASH_VALUE_OPTIONS and index + 1 < len(argv):
            value = argv[index + 1]
            if value.startswith("-") and not value.startswith("--"):
                normalized.append(f"{item}={value}")
                index += 2
                continue
        normalized.append(item)
        index += 1
    return normalized


def _system_exit_code(exc: SystemExit) -> int:
    if isinstance(exc.code, int):
        return exc.code
    if exc.code is None:
        return 0
    return 1


def _cmd_histogram(args: argparse.Namespace) -> int:
    bounds_values = parse_float_list(args.bounds, name="bounds")
    if len(bounds_values) != 2:
        raise ReleaseCardError("bounds must contain exactly two numbers: lower,upper")
    bounds = (bounds_values[0], bounds_values[1])
    bin_edges = parse_float_list(args.bins, name="bins")
    validate_histogram_policy(
        epsilon=args.epsilon,
        bounds=bounds,
        bin_edges=bin_edges,
        strict=args.strict,
    )
    _validate_output_paths(
        input_path=args.input,
        out_path=args.out,
        receipt_path=args.receipt,
        card_path=args.card,
    )
    secret_from_env(args.signing_key_env)
    values = read_numeric_column(args.input, args.column)

    release = release_histogram(
        values,
        epsilon=args.epsilon,
        bounds=bounds,
        bin_edges=bin_edges,
        strict=args.strict,
    )
    policy = {
        "query_type": "histogram",
        "n": len(values),
        "column": args.column,
        "epsilon": args.epsilon,
        "bounds": [bounds[0], bounds[1]],
        "bin_edges": bin_edges,
        "mechanism": MECHANISM,
        "sensitivity": HISTOGRAM_SENSITIVITY,
        "proof_scope": PROOF_SCOPE,
        "strict_finite_precision": True,
    }
    receipt = build_receipt(
        release=release,
        public_policy=policy,
        signing_key_env=args.signing_key_env,
    )

    _write_outputs_atomically(
        out_path=Path(args.out),
        receipt_path=Path(args.receipt),
        card_path=Path(args.card),
        release=release,
        receipt=receipt,
    )
    print(f"wrote release: {args.out}")
    print(f"wrote receipt: {args.receipt}")
    print(f"wrote card: {args.card}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    receipt = load_json(args.receipt)
    verify_receipt(receipt, signing_key_env=args.signing_key_env)
    if args.release:
        release = load_json(args.release)
        verify_release_digest(release, receipt)
        print(f"receipt and release verified: {receipt['release_digest']}")
    else:
        print(f"receipt verified: {receipt['release_digest']}")
    return 0


def _write_outputs_atomically(
    *,
    out_path: Path,
    receipt_path: Path,
    card_path: Path,
    release: dict,
    receipt: dict,
) -> None:
    writers: list[tuple[Path, Callable[[Path], None]]] = [
        (out_path, lambda path: write_json(path, release)),
        (receipt_path, lambda path: write_json(path, receipt)),
        (card_path, lambda path: write_card(path, release=release, receipt=receipt)),
    ]
    temp_records: list[tuple[Path, Path]] = []
    try:
        for target, writer in writers:
            temp_path = _make_temp_output_path(target)
            temp_records.append((temp_path, target))
            writer(temp_path)
        for temp_path, target in temp_records:
            try:
                os.replace(temp_path, target)
            except OSError as exc:
                raise ReleaseCardError(f"cannot replace output file: {target}: {exc}") from exc
    finally:
        for temp_path, _target in temp_records:
            temp_path.unlink(missing_ok=True)


def _make_temp_output_path(target: Path) -> Path:
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            delete=False,
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
        ) as temp_file:
            return Path(temp_file.name)
    except OSError as exc:
        raise ReleaseCardError(
            f"cannot create temporary output file for {target}: {exc}"
        ) from exc


def _normalize_path(path: str) -> str:
    return os.path.normcase(str(Path(path).expanduser().resolve(strict=False)))


def _validate_output_paths(
    *,
    input_path: str,
    out_path: str,
    receipt_path: str,
    card_path: str,
) -> None:
    input_norm = _normalize_path(input_path)
    output_paths = {
        "--out": out_path,
        "--receipt": receipt_path,
        "--card": card_path,
    }
    outputs = {
        "--out": _normalize_path(out_path),
        "--receipt": _normalize_path(receipt_path),
        "--card": _normalize_path(card_path),
    }
    seen: dict[str, str] = {}
    for label, normalized in outputs.items():
        if normalized == input_norm:
            raise ReleaseCardError(f"{label} must not overwrite the input CSV")
        if normalized in seen:
            raise ReleaseCardError(f"{label} must be different from {seen[normalized]}")
        seen[normalized] = label
    labels = list(outputs)
    for index, left_label in enumerate(labels):
        for right_label in labels[index + 1 :]:
            _validate_output_paths_are_not_nested(
                left_label,
                outputs[left_label],
                right_label,
                outputs[right_label],
            )
    for label, output_path in output_paths.items():
        _validate_single_output_path(label, output_path)


def _validate_output_paths_are_not_nested(
    left_label: str,
    left_path: str,
    right_label: str,
    right_path: str,
) -> None:
    try:
        common = os.path.commonpath([left_path, right_path])
    except ValueError:
        return
    if common == left_path:
        raise ReleaseCardError(f"{right_label} must not be inside {left_label}")
    if common == right_path:
        raise ReleaseCardError(f"{left_label} must not be inside {right_label}")


def _validate_single_output_path(label: str, output_path: str) -> None:
    path = Path(output_path).expanduser()
    if path.exists():
        if path.is_dir():
            raise ReleaseCardError(f"{label} must be a file path, not a directory")
        if not os.access(path, os.W_OK):
            raise ReleaseCardError(f"{label} is not writable: {path}")
        return

    parent = _nearest_existing_parent(path)
    if not parent.is_dir():
        raise ReleaseCardError(f"{label} parent path is not a directory: {parent}")
    if not os.access(parent, os.W_OK):
        raise ReleaseCardError(f"{label} parent directory is not writable: {parent}")


def _nearest_existing_parent(path: Path) -> Path:
    parent = path.parent
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    return parent


if __name__ == "__main__":
    raise SystemExit(main())
