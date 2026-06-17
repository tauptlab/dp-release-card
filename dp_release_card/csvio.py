from __future__ import annotations

import csv
import math
from pathlib import Path

from .errors import ReleaseCardError


def read_numeric_column(path: str | Path, column: str) -> list[float]:
    """Read one finite numeric CSV column.

    This function intentionally returns only the parsed values to the in-process
    caller. Release and receipt surfaces must not echo raw samples.
    """

    path = Path(path)
    if not path.exists():
        raise ReleaseCardError(f"input CSV does not exist: {path}")
    if not path.is_file():
        raise ReleaseCardError(f"input CSV is not a file: {path}")
    if not column or column.strip() == "":
        raise ReleaseCardError("column is required")

    values: list[float] = []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise ReleaseCardError("input CSV is missing a header row")
            if any(field is None or field.strip() == "" for field in reader.fieldnames):
                raise ReleaseCardError("input CSV has a blank header name")
            duplicate_headers = _duplicate_items(reader.fieldnames)
            if duplicate_headers:
                names = ", ".join(repr(name) for name in duplicate_headers)
                raise ReleaseCardError(f"input CSV has duplicate header names: {names}")
            if column not in reader.fieldnames:
                available = ", ".join(reader.fieldnames)
                raise ReleaseCardError(
                    f"column {column!r} not found; available columns: {available}"
                )

            for row_index, row in enumerate(reader, start=2):
                if None in row:
                    raise ReleaseCardError(f"row {row_index}: too many fields")
                if any(value is None for value in row.values()):
                    raise ReleaseCardError(f"row {row_index}: too few fields")
                raw = row.get(column, "")
                if raw is None or raw.strip() == "":
                    raise ReleaseCardError(f"row {row_index}: column {column!r} is blank")
                try:
                    value = float(raw)
                except ValueError as exc:
                    raise ReleaseCardError(
                        f"row {row_index}: column {column!r} is not numeric"
                    ) from exc
                if not math.isfinite(value):
                    raise ReleaseCardError(f"row {row_index}: column {column!r} is not finite")
                values.append(value)
    except OSError as exc:
        raise ReleaseCardError(f"cannot read input CSV: {path}: {exc}") from exc
    except UnicodeError as exc:
        raise ReleaseCardError(f"input CSV is not valid UTF-8: {path}") from exc

    if not values:
        raise ReleaseCardError("input CSV contains no data rows")
    return values


def _duplicate_items(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates
