from pathlib import Path

import pytest

from dp_release_card.csvio import read_numeric_column
from dp_release_card.errors import ReleaseCardError


def test_read_numeric_column_success(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("age,name\n10,a\n20,b\n30,c\n", encoding="utf-8")

    assert read_numeric_column(path, "age") == [10.0, 20.0, 30.0]


def test_read_numeric_column_rejects_missing_column(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("age\n10\n", encoding="utf-8")

    with pytest.raises(ReleaseCardError, match="not found"):
        read_numeric_column(path, "income")


def test_read_numeric_column_rejects_directory_input(tmp_path: Path) -> None:
    with pytest.raises(ReleaseCardError, match="not a file"):
        read_numeric_column(tmp_path, "age")


def test_read_numeric_column_rejects_non_utf8(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_bytes(b"\xff\xfe\x00\x00")

    with pytest.raises(ReleaseCardError, match="not valid UTF-8"):
        read_numeric_column(path, "age")


def test_read_numeric_column_rejects_non_numeric(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("age\n10\nunknown\n", encoding="utf-8")

    with pytest.raises(ReleaseCardError, match="not numeric"):
        read_numeric_column(path, "age")


def test_read_numeric_column_rejects_non_finite(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("age\n10\nNaN\n", encoding="utf-8")

    with pytest.raises(ReleaseCardError, match="not finite"):
        read_numeric_column(path, "age")


def test_read_numeric_column_rejects_duplicate_header(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("age,age\n10,20\n", encoding="utf-8")

    with pytest.raises(ReleaseCardError, match="duplicate header"):
        read_numeric_column(path, "age")


def test_read_numeric_column_rejects_blank_header(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("age,\n10,x\n", encoding="utf-8")

    with pytest.raises(ReleaseCardError, match="blank header"):
        read_numeric_column(path, "age")


def test_read_numeric_column_rejects_whitespace_only_header(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("age,   \n10,x\n", encoding="utf-8")

    with pytest.raises(ReleaseCardError, match="blank header"):
        read_numeric_column(path, "age")


def test_read_numeric_column_rejects_whitespace_only_column(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("age\n10\n", encoding="utf-8")

    with pytest.raises(ReleaseCardError, match="column is required"):
        read_numeric_column(path, "   ")


def test_read_numeric_column_rejects_extra_fields(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("age,name\n10,a,extra\n", encoding="utf-8")

    with pytest.raises(ReleaseCardError, match="too many fields"):
        read_numeric_column(path, "age")


def test_read_numeric_column_rejects_blank(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("age,name\n10,a\n,b\n", encoding="utf-8")

    with pytest.raises(ReleaseCardError, match="blank"):
        read_numeric_column(path, "age")
