import hashlib
import hmac
import json
import os
import subprocess
import sys
from pathlib import Path

from dp_release_card.cli import main
from dp_release_card.errors import ReleaseCardError
from dp_release_card.receipt import canonical_json_bytes


def test_cli_main_returns_usage_error_without_raising(capsys) -> None:
    code = main([])

    captured = capsys.readouterr()
    assert code == 2
    assert "missing command" in captured.err
    assert "Traceback" not in captured.err


def test_cli_main_returns_required_argument_error_without_raising(capsys) -> None:
    code = main(["verify", "receipt.json"])

    captured = capsys.readouterr()
    assert code == 2
    assert "--signing-key-env" in captured.err
    assert "Traceback" not in captured.err


def test_cli_main_returns_success_for_help(capsys) -> None:
    code = main(["--help"])

    captured = capsys.readouterr()
    assert code == 0
    assert "Generate verifiable DP release cards" in captured.out
    assert captured.err == ""


def test_cli_histogram_and_verify(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age\n10\n20\n30\n101\n", encoding="utf-8")

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    assert code == 0
    assert release_path.exists()
    assert receipt_path.exists()
    assert card_path.exists()
    release = json.loads(release_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert release["query_type"] == "histogram"
    assert release["mechanism"] == "discrete_laplace"
    assert receipt["public_policy"]["n"] == 4
    public_policy_text = json.dumps(receipt["public_policy"], sort_keys=True)
    assert "101" not in public_policy_text

    assert main(["verify", str(receipt_path), "--signing-key-env", "DP_RELEASE_CARD_SECRET"]) == 0


def test_cli_verify_release_digest(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age\n10\n20\n30\n", encoding="utf-8")
    assert (
        main(
            [
                "histogram",
                str(csv_path),
                "--column",
                "age",
                "--epsilon",
                "1",
                "--bounds",
                "0,100",
                "--bins",
                "0,50,100",
                "--strict",
                "--out",
                str(release_path),
                "--receipt",
                str(receipt_path),
                "--card",
                str(card_path),
                "--signing-key-env",
                "DP_RELEASE_CARD_SECRET",
            ]
        )
        == 0
    )

    code = main(
        [
            "verify",
            str(receipt_path),
            "--release",
            str(release_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert "receipt and release verified" in captured.out


def test_cli_histogram_accepts_negative_public_bounds_and_creates_output_dirs(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    output_dir = tmp_path / "nested" / "outputs"
    release_path = output_dir / "release.json"
    receipt_path = output_dir / "receipt.json"
    card_path = output_dir / "release-card.md"
    csv_path.write_text("age\n-20\n-10\n0\n9.9\n10\n20\n", encoding="utf-8")

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "-10,10",
            "--bins",
            "-10,0,10",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    assert code == 0
    assert release_path.exists()
    assert receipt_path.exists()
    assert card_path.exists()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["public_policy"]["bounds"] == [-10.0, 10.0]
    assert receipt["public_policy"]["bin_edges"] == [-10.0, 0.0, 10.0]


def test_python_module_cli_histogram_and_verify(tmp_path: Path) -> None:
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age\n10\n20\n30\n", encoding="utf-8")
    env = {
        **os.environ,
        "DP_RELEASE_CARD_SECRET": "test-secret",
    }

    histogram = subprocess.run(
        [
            sys.executable,
            "-m",
            "dp_release_card",
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ],
        env=env,
        stdin=subprocess.DEVNULL,
        text=True,
        capture_output=True,
        check=False,
    )
    assert histogram.returncode == 0, histogram.stderr

    verify = subprocess.run(
        [
            sys.executable,
            "-m",
            "dp_release_card",
            "verify",
            str(receipt_path),
            "--release",
            str(release_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ],
        env=env,
        stdin=subprocess.DEVNULL,
        text=True,
        capture_output=True,
        check=False,
    )
    assert verify.returncode == 0, verify.stderr
    assert "receipt and release verified" in verify.stdout


def test_cli_verify_release_digest_rejects_tampered_release(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age\n10\n20\n30\n", encoding="utf-8")
    assert (
        main(
            [
                "histogram",
                str(csv_path),
                "--column",
                "age",
                "--epsilon",
                "1",
                "--bounds",
                "0,100",
                "--bins",
                "0,50,100",
                "--strict",
                "--out",
                str(release_path),
                "--receipt",
                str(receipt_path),
                "--card",
                str(card_path),
                "--signing-key-env",
                "DP_RELEASE_CARD_SECRET",
            ]
        )
        == 0
    )
    release = json.loads(release_path.read_text(encoding="utf-8"))
    release["values"] = [value + 1 for value in release["values"]]
    release_path.write_text(json.dumps(release), encoding="utf-8")

    code = main(
        [
            "verify",
            str(receipt_path),
            "--release",
            str(release_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "release digest does not match" in captured.err


def test_cli_verify_release_rejects_signed_policy_mismatch(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
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
    policy = {
        "query_type": "histogram",
        "n": 2,
        "column": "age",
        "epsilon": 2.0,
        "bounds": [0, 100],
        "bin_edges": [0, 50, 100],
        "mechanism": "discrete_laplace",
        "sensitivity": 2.0,
        "proof_scope": "strict_finite_precision",
        "strict_finite_precision": True,
    }
    payload = {
        "version": "dp-release-card.receipt.v1",
        "tool_version": "0.1.0",
        "created_at": "2026-06-17T00:00:00Z",
        "release_digest": hashlib.sha256(canonical_json_bytes(release)).hexdigest(),
        "public_policy": policy,
    }
    receipt = {
        **payload,
        "signature": {
            "algorithm": "hmac-sha256",
            "key_env": "DP_RELEASE_CARD_SECRET",
            "value": hmac.new(
                b"test-secret",
                canonical_json_bytes(payload),
                hashlib.sha256,
            ).hexdigest(),
        },
    }
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    release_path.write_text(json.dumps(release), encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    code = main(
        [
            "verify",
            str(receipt_path),
            "--release",
            str(release_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "epsilon_spent" in captured.err


def test_cli_verify_rejects_tampered_receipt(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(
        json.dumps(
            {
                "version": "dp-release-card.receipt.v1",
                "tool_version": "0.1.0",
                "created_at": "2026-06-15T00:00:00Z",
                "release_digest": "tampered",
                "public_policy": {"n": 1},
                "signature": {
                    "algorithm": "hmac-sha256",
                    "key_env": "DP_RELEASE_CARD_SECRET",
                    "value": "bad",
                },
            }
        ),
        encoding="utf-8",
    )

    assert main(["verify", str(receipt_path), "--signing-key-env", "DP_RELEASE_CARD_SECRET"]) == 1


def test_cli_verify_missing_receipt_without_traceback(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")

    code = main(
        [
            "verify",
            str(tmp_path / "missing-receipt.json"),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "cannot read JSON" in captured.err
    assert "Traceback" not in captured.err


def test_cli_verify_non_utf8_receipt_without_traceback(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(b"\xff\xfe\x00\x00")

    code = main(["verify", str(receipt_path), "--signing-key-env", "DP_RELEASE_CARD_SECRET"])

    captured = capsys.readouterr()
    assert code == 1
    assert "not valid UTF-8" in captured.err
    assert "Traceback" not in captured.err


def test_cli_verify_rejects_duplicate_json_key_without_traceback(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text('{"version":"bad","version":"also-bad"}', encoding="utf-8")

    code = main(["verify", str(receipt_path), "--signing-key-env", "DP_RELEASE_CARD_SECRET"])

    captured = capsys.readouterr()
    assert code == 1
    assert "duplicate key" in captured.err
    assert "Traceback" not in captured.err


def test_cli_verify_rejects_non_standard_json_without_traceback(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text('{"version": NaN}', encoding="utf-8")

    code = main(["verify", str(receipt_path), "--signing-key-env", "DP_RELEASE_CARD_SECRET"])

    captured = capsys.readouterr()
    assert code == 1
    assert "non-standard numeric constant" in captured.err
    assert "Traceback" not in captured.err


def test_cli_verify_signed_malformed_receipt_without_traceback(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    payload = {
        "version": "dp-release-card.receipt.v1",
        "tool_version": "0.1.0",
        "created_at": "2026-06-17T00:00:00Z",
        "public_policy": {"n": 1},
    }
    receipt = {
        **payload,
        "signature": {
            "algorithm": "hmac-sha256",
            "key_env": "DP_RELEASE_CARD_SECRET",
            "value": hmac.new(
                b"test-secret",
                canonical_json_bytes(payload),
                hashlib.sha256,
            ).hexdigest(),
        },
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    code = main(["verify", str(receipt_path), "--signing-key-env", "DP_RELEASE_CARD_SECRET"])

    captured = capsys.readouterr()
    assert code == 1
    assert "release_digest" in captured.err
    assert "Traceback" not in captured.err


def test_cli_invalid_policy_fails_before_outputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age\n10\n20\n", encoding="utf-8")

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,90",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    assert code == 1
    assert not release_path.exists()
    assert not receipt_path.exists()
    assert not card_path.exists()


def test_cli_rejects_duplicate_output_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    shared_path = tmp_path / "shared.out"
    csv_path.write_text("age\n10\n20\n", encoding="utf-8")

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(shared_path),
            "--receipt",
            str(shared_path),
            "--card",
            str(shared_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    assert code == 1
    assert not shared_path.exists()


def test_cli_rejects_output_overwriting_input(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    original_csv = "age\n10\n20\n"
    csv_path.write_text(original_csv, encoding="utf-8")

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(csv_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    assert code == 1
    assert csv_path.read_text(encoding="utf-8") == original_csv
    assert not receipt_path.exists()
    assert not card_path.exists()


def test_cli_requires_secret_before_reading_input(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("DP_RELEASE_CARD_SECRET", raising=False)
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"

    code = main(
        [
            "histogram",
            str(tmp_path / "missing.csv"),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "signing key env var" in captured.err
    assert "input CSV does not exist" not in captured.err
    assert not release_path.exists()
    assert not receipt_path.exists()
    assert not card_path.exists()


def test_cli_rejects_output_parent_that_is_file(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    parent_file = tmp_path / "not-a-dir"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age\n10\n20\n", encoding="utf-8")
    parent_file.write_text("x", encoding="utf-8")

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(parent_file / "release.json"),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "parent path is not a directory" in captured.err
    assert "Traceback" not in captured.err
    assert not receipt_path.exists()
    assert not card_path.exists()


def test_cli_rejects_output_target_that_is_directory(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_dir = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age\n10\n20\n", encoding="utf-8")
    release_dir.mkdir()

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_dir),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "not a directory" in captured.err
    assert "Traceback" not in captured.err
    assert not receipt_path.exists()
    assert not card_path.exists()


def test_cli_rejects_read_only_output_before_partial_write(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age\n10\n20\n", encoding="utf-8")
    receipt_path.write_text("locked", encoding="utf-8")
    receipt_path.chmod(0o444)

    try:
        code = main(
            [
                "histogram",
                str(csv_path),
                "--column",
                "age",
                "--epsilon",
                "1",
                "--bounds",
                "0,100",
                "--bins",
                "0,50,100",
                "--strict",
                "--out",
                str(release_path),
                "--receipt",
                str(receipt_path),
                "--card",
                str(card_path),
                "--signing-key-env",
                "DP_RELEASE_CARD_SECRET",
            ]
        )
    finally:
        receipt_path.chmod(0o666)

    captured = capsys.readouterr()
    assert code == 1
    assert "not writable" in captured.err
    assert not release_path.exists()
    assert receipt_path.read_text(encoding="utf-8") == "locked"
    assert not card_path.exists()


def test_cli_preserves_existing_outputs_when_card_write_fails(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age\n10\n20\n", encoding="utf-8")
    release_path.write_text("old-release", encoding="utf-8")
    receipt_path.write_text("old-receipt", encoding="utf-8")
    card_path.write_text("old-card", encoding="utf-8")

    def fail_card(*args, **kwargs):
        raise ReleaseCardError("simulated card write failure")

    monkeypatch.setattr("dp_release_card.cli.write_card", fail_card)

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "simulated card write failure" in captured.err
    assert release_path.read_text(encoding="utf-8") == "old-release"
    assert receipt_path.read_text(encoding="utf-8") == "old-receipt"
    assert card_path.read_text(encoding="utf-8") == "old-card"
    assert list(tmp_path.glob(".*.tmp")) == []


def test_cli_rolls_back_existing_outputs_when_replace_fails(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age\n10\n20\n", encoding="utf-8")
    release_path.write_text("old-release", encoding="utf-8")
    receipt_path.write_text("old-receipt", encoding="utf-8")
    card_path.write_text("old-card", encoding="utf-8")
    original_replace = os.replace
    failed_once = False

    def fail_receipt_replace_once(src, dst):
        nonlocal failed_once
        if not failed_once and Path(dst) == receipt_path:
            failed_once = True
            raise OSError("simulated replace failure")
        return original_replace(src, dst)

    monkeypatch.setattr("dp_release_card.cli.os.replace", fail_receipt_replace_once)

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "cannot replace output file" in captured.err
    assert release_path.read_text(encoding="utf-8") == "old-release"
    assert receipt_path.read_text(encoding="utf-8") == "old-receipt"
    assert card_path.read_text(encoding="utf-8") == "old-card"
    assert list(tmp_path.glob(".*.tmp")) == []


def test_cli_cleans_temp_file_when_backup_prepare_fails(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age\n10\n20\n", encoding="utf-8")
    release_path.write_text("old-release", encoding="utf-8")
    receipt_path.write_text("old-receipt", encoding="utf-8")
    card_path.write_text("old-card", encoding="utf-8")
    original_replace = os.replace

    def fail_release_backup_prepare(src, dst):
        if Path(src) == release_path and Path(dst).name.startswith(".release.json."):
            raise OSError("simulated prepare failure")
        return original_replace(src, dst)

    monkeypatch.setattr("dp_release_card.cli.os.replace", fail_release_backup_prepare)

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "cannot prepare existing output file" in captured.err
    assert release_path.read_text(encoding="utf-8") == "old-release"
    assert receipt_path.read_text(encoding="utf-8") == "old-receipt"
    assert card_path.read_text(encoding="utf-8") == "old-card"
    assert list(tmp_path.glob(".*.tmp")) == []


def test_cli_rejects_output_under_file_path_before_partial_write(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    parent_file = tmp_path / "not-a-dir"
    release_path = tmp_path / "release.json"
    receipt_path = parent_file / "nested" / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age\n10\n20\n", encoding="utf-8")
    parent_file.write_text("x", encoding="utf-8")

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "parent path is not a directory" in captured.err
    assert not release_path.exists()
    assert not card_path.exists()


def test_cli_rejects_nested_output_paths_before_partial_write(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "out"
    receipt_path = release_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age\n10\n20\n", encoding="utf-8")

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "inside --out" in captured.err
    assert not release_path.exists()
    assert not card_path.exists()


def test_cli_rejects_tiny_epsilon_without_traceback(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age\n10\n20\n", encoding="utf-8")

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1e-320",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "too small" in captured.err
    assert "Traceback" not in captured.err
    assert not release_path.exists()
    assert not receipt_path.exists()
    assert not card_path.exists()


def test_cli_rejects_duplicate_csv_header_without_outputs(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age,age\n10,20\n", encoding="utf-8")

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "duplicate header" in captured.err
    assert not release_path.exists()
    assert not receipt_path.exists()
    assert not card_path.exists()


def test_cli_rejects_csv_extra_fields_without_outputs(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age,name\n10,a,extra\n", encoding="utf-8")

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "too many fields" in captured.err
    assert not release_path.exists()
    assert not receipt_path.exists()
    assert not card_path.exists()


def test_cli_rejects_csv_missing_fields_without_outputs(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age,name\n10\n", encoding="utf-8")

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "too few fields" in captured.err
    assert not release_path.exists()
    assert not receipt_path.exists()
    assert not card_path.exists()


def test_cli_rejects_csv_blank_row_without_outputs(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_text("age\n10\n\n20\n", encoding="utf-8")

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "blank row" in captured.err
    assert not release_path.exists()
    assert not receipt_path.exists()
    assert not card_path.exists()


def test_cli_rejects_directory_input_without_outputs(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    input_dir = tmp_path / "input-dir"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    input_dir.mkdir()

    code = main(
        [
            "histogram",
            str(input_dir),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "not a file" in captured.err
    assert not release_path.exists()
    assert not receipt_path.exists()
    assert not card_path.exists()


def test_cli_rejects_non_utf8_csv_without_outputs(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DP_RELEASE_CARD_SECRET", "test-secret")
    csv_path = tmp_path / "ages.csv"
    release_path = tmp_path / "release.json"
    receipt_path = tmp_path / "receipt.json"
    card_path = tmp_path / "release-card.md"
    csv_path.write_bytes(b"\xff\xfe\x00\x00")

    code = main(
        [
            "histogram",
            str(csv_path),
            "--column",
            "age",
            "--epsilon",
            "1",
            "--bounds",
            "0,100",
            "--bins",
            "0,50,100",
            "--strict",
            "--out",
            str(release_path),
            "--receipt",
            str(receipt_path),
            "--card",
            str(card_path),
            "--signing-key-env",
            "DP_RELEASE_CARD_SECRET",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "not valid UTF-8" in captured.err
    assert "Traceback" not in captured.err
    assert not release_path.exists()
    assert not receipt_path.exists()
    assert not card_path.exists()
