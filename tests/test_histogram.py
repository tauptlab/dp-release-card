import pytest

from dp_release_card.errors import ReleaseCardError
from dp_release_card.histogram import (
    HISTOGRAM_SENSITIVITY,
    dense_histogram,
    release_histogram,
    sample_discrete_laplace,
    validate_discrete_laplace_params,
    validate_histogram_policy,
)


def test_dense_histogram_clamps_to_public_bounds_and_bins() -> None:
    counts = dense_histogram(
        [-1, 0, 19, 20, 100, 101],
        bounds=(0, 100),
        bin_edges=[0, 20, 40, 100],
    )

    assert counts == [3, 1, 2]


@pytest.mark.parametrize(
    "bounds, bin_edges",
    [
        ((0,), [0, 1]),
        ((0, 1), [0]),
        ((0, 2), [0, 2, 1]),
        ((0, 1), [0, 2]),
        ((False, 1), [0, 1]),
        ((0, 1), [0, True]),
    ],
)
def test_dense_histogram_rejects_invalid_geometry(bounds, bin_edges) -> None:
    with pytest.raises(ReleaseCardError):
        dense_histogram([1], bounds=bounds, bin_edges=bin_edges)


def test_release_histogram_public_schema_has_no_raw_fields() -> None:
    release = release_histogram(
        [1, 2, 3, 80],
        epsilon=1.0,
        bounds=(0, 100),
        bin_edges=[0, 50, 100],
        strict=True,
        noise_fn=lambda: 0,
    )

    assert release == {
        "query_type": "histogram",
        "values": [3, 1],
        "bin_edges_used": [0, 50, 100],
        "epsilon_spent": 1.0,
        "mechanism": "discrete_laplace",
        "sensitivity": HISTOGRAM_SENSITIVITY,
        "proof_scope": "strict_finite_precision",
        "warnings": release["warnings"],
    }
    forbidden = {"raw", "sample", "true", "pre_noise", "input_file_hash"}
    flattened_keys = " ".join(release.keys()).lower()
    assert not any(name in flattened_keys for name in forbidden)


def test_release_histogram_clamps_negative_noisy_counts() -> None:
    release = release_histogram(
        [10, 80],
        epsilon=1.0,
        bounds=(0, 100),
        bin_edges=[0, 50, 100],
        strict=True,
        noise_fn=lambda: -10,
    )

    assert release["values"] == [0, 0]
    assert any("clamped to zero" in warning for warning in release["warnings"])


def test_release_histogram_accepts_integer_valued_float_noise() -> None:
    release = release_histogram(
        [10, 80],
        epsilon=1.0,
        bounds=(0, 100),
        bin_edges=[0, 50, 100],
        strict=True,
        noise_fn=lambda: 0.0,
    )

    assert release["values"] == [1, 1]


@pytest.mark.parametrize("noise", [float("nan"), "oops", True, 1.5])
def test_release_histogram_rejects_invalid_noise_fn_output(noise) -> None:
    with pytest.raises(ReleaseCardError, match="noise_fn"):
        release_histogram(
            [10, 80],
            epsilon=1.0,
            bounds=(0, 100),
            bin_edges=[0, 50, 100],
            strict=True,
            noise_fn=lambda: noise,
        )


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"epsilon": 0, "bounds": (0, 1), "bin_edges": [0, 1], "strict": True}, "epsilon"),
        ({"epsilon": 1, "bounds": (1, 0), "bin_edges": [0, 1], "strict": True}, "bounds"),
        ({"epsilon": 1, "bounds": (0, 1), "bin_edges": [0], "strict": True}, "bins"),
        ({"epsilon": 1, "bounds": (0, 1), "bin_edges": [0, 0.5, 0.5], "strict": True}, "bins"),
        ({"epsilon": 1, "bounds": (0, 1), "bin_edges": [0, 2], "strict": True}, "bounds"),
        ({"epsilon": 1, "bounds": (0, 1), "bin_edges": [0, 1], "strict": False}, "strict"),
        ({"epsilon": True, "bounds": (0, 1), "bin_edges": [0, 1], "strict": True}, "epsilon"),
    ],
)
def test_validate_histogram_policy_rejects_invalid_public_policy(kwargs, message) -> None:
    with pytest.raises(ReleaseCardError, match=message):
        validate_histogram_policy(**kwargs)


def test_discrete_laplace_validation_rejects_invalid_params() -> None:
    with pytest.raises(ReleaseCardError, match="epsilon"):
        validate_discrete_laplace_params(epsilon=-1, sensitivity=1)
    with pytest.raises(ReleaseCardError, match="sensitivity"):
        validate_discrete_laplace_params(epsilon=1, sensitivity=0)
    with pytest.raises(ReleaseCardError, match="sensitivity"):
        validate_discrete_laplace_params(epsilon=1, sensitivity=True)
    with pytest.raises(ReleaseCardError, match="alpha"):
        sample_discrete_laplace(float("inf"))
    with pytest.raises(ReleaseCardError, match="alpha"):
        sample_discrete_laplace(True)
    with pytest.raises(ReleaseCardError, match="too small"):
        validate_discrete_laplace_params(epsilon=1e-320, sensitivity=2.0)
    with pytest.raises(ReleaseCardError, match="too small"):
        sample_discrete_laplace(1e-320)


@pytest.mark.parametrize("rng_value", [-0.1, 1.0, float("nan"), True, "0.5"])
def test_discrete_laplace_rejects_invalid_rng_output(rng_value) -> None:
    class FixedRng:
        def random(self):
            return rng_value

    with pytest.raises(ReleaseCardError, match="rng.random"):
        sample_discrete_laplace(1.0, rng=FixedRng())
