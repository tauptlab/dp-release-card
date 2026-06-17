from __future__ import annotations

import bisect
import math
import random

from .errors import ReleaseCardError

HISTOGRAM_SENSITIVITY = 2.0
MECHANISM = "discrete_laplace"
PROOF_SCOPE = "strict_finite_precision"
QUERY_TYPE = "histogram"


def parse_float_list(raw: str, *, name: str) -> list[float]:
    if not isinstance(raw, str) or raw.strip() == "":
        raise ReleaseCardError(f"{name} is required")
    out: list[float] = []
    for part in raw.split(","):
        piece = part.strip()
        if piece == "":
            raise ReleaseCardError(f"{name} contains an empty item")
        try:
            value = float(piece)
        except ValueError as exc:
            raise ReleaseCardError(f"{name} item {piece!r} is not numeric") from exc
        if not math.isfinite(value):
            raise ReleaseCardError(f"{name} item {piece!r} is not finite")
        out.append(value)
    return out


def validate_histogram_policy(
    *,
    epsilon: float,
    bounds: tuple[float, float],
    bin_edges: list[float],
    strict: bool,
) -> None:
    if not _is_finite_number(epsilon) or epsilon <= 0:
        raise ReleaseCardError(f"epsilon must be positive finite, got {epsilon!r}")
    if strict is not True:
        raise ReleaseCardError("v1 only supports --strict discrete_laplace releases")

    validate_histogram_geometry(bounds=bounds, bin_edges=bin_edges)
    validate_discrete_laplace_params(epsilon=epsilon, sensitivity=HISTOGRAM_SENSITIVITY)


def validate_histogram_geometry(
    *,
    bounds: tuple[float, float],
    bin_edges: list[float],
) -> None:
    if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
        raise ReleaseCardError(f"bounds must contain exactly two numbers, got {bounds!r}")
    lo, hi = bounds
    if not _is_finite_number(lo) or not _is_finite_number(hi) or hi <= lo:
        raise ReleaseCardError(f"bounds must be finite with upper > lower, got {bounds!r}")
    if not isinstance(bin_edges, list):
        raise ReleaseCardError("bins must be a list of edges")
    if len(bin_edges) < 2:
        raise ReleaseCardError("bins must contain at least two edges")
    if any(not _is_finite_number(edge) for edge in bin_edges):
        raise ReleaseCardError("bins must be finite")
    for prev, cur in zip(bin_edges, bin_edges[1:]):
        if cur <= prev:
            raise ReleaseCardError("bins must be strictly increasing")
    if bin_edges[0] != lo or bin_edges[-1] != hi:
        raise ReleaseCardError("v1 requires bins to start/end exactly at the public bounds")


def release_histogram(
    values: list[float],
    *,
    epsilon: float,
    bounds: tuple[float, float],
    bin_edges: list[float],
    strict: bool,
    noise_fn=None,
) -> dict:
    if not values:
        raise ReleaseCardError("values must be non-empty")
    validate_histogram_policy(
        epsilon=epsilon,
        bounds=bounds,
        bin_edges=bin_edges,
        strict=strict,
    )

    counts = dense_histogram(values, bounds=bounds, bin_edges=bin_edges)
    if noise_fn is None:
        alpha = epsilon / HISTOGRAM_SENSITIVITY
        noise_fn = lambda: sample_discrete_laplace(alpha)

    noisy_counts = [
        postprocess_histogram_count(count + _coerce_noise_value(noise_fn()))
        for count in counts
    ]
    return {
        "query_type": QUERY_TYPE,
        "values": noisy_counts,
        "bin_edges_used": bin_edges[:],
        "epsilon_spent": epsilon,
        "mechanism": MECHANISM,
        "sensitivity": HISTOGRAM_SENSITIVITY,
        "proof_scope": PROOF_SCOPE,
        "warnings": [
            "bounds and bin_edges are caller-attested public metadata; deriving them from private data is outside this tool's DP contract",
            "negative noisy bin counts are clamped to zero by public post-processing; this costs no additional privacy budget but can add bias",
            "production TaupT routing, AutoBound, fairness calibration, and service workflow are not included",
        ],
    }


def dense_histogram(
    values: list[float],
    *,
    bounds: tuple[float, float],
    bin_edges: list[float],
) -> list[int]:
    validate_histogram_geometry(bounds=bounds, bin_edges=bin_edges)
    lo, hi = bounds
    counts = [0 for _ in range(len(bin_edges) - 1)]
    for value in values:
        if not _is_finite_number(value):
            raise ReleaseCardError("values must be finite numbers")
        clamped = min(max(value, lo), hi)
        if clamped == bin_edges[-1]:
            idx = len(counts) - 1
        else:
            idx = bisect.bisect_right(bin_edges, clamped) - 1
            idx = max(0, min(idx, len(counts) - 1))
        counts[idx] += 1
    return counts


def validate_discrete_laplace_params(*, epsilon: float, sensitivity: float) -> None:
    if not _is_finite_number(epsilon) or epsilon <= 0:
        raise ReleaseCardError(f"epsilon must be positive finite, got {epsilon!r}")
    if not _is_finite_number(sensitivity) or sensitivity <= 0:
        raise ReleaseCardError(f"sensitivity must be positive finite, got {sensitivity!r}")
    alpha = epsilon / sensitivity
    if not math.isfinite(alpha) or alpha <= 0:
        raise ReleaseCardError("discrete_laplace alpha must be positive finite")
    if math.exp(-alpha) >= 1.0:
        raise ReleaseCardError(
            "discrete_laplace alpha is too small for this finite-precision sampler"
        )


def postprocess_histogram_count(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ReleaseCardError("histogram count must be an integer")
    return max(0, value)


def _coerce_noise_value(value: object) -> int:
    if isinstance(value, bool):
        raise ReleaseCardError("noise_fn must return finite integer noise")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    raise ReleaseCardError("noise_fn must return finite integer noise")


def sample_discrete_laplace(alpha: float, *, rng: random.Random | None = None) -> int:
    """Sample two-sided geometric noise with pmf proportional to exp(-alpha*abs(k))."""

    if not _is_finite_number(alpha) or alpha <= 0:
        raise ReleaseCardError(f"alpha must be positive finite, got {alpha!r}")
    q = math.exp(-alpha)
    if q >= 1.0:
        raise ReleaseCardError("alpha is too small for this finite-precision sampler")
    if q <= 0:
        return 0
    rng = rng or random.SystemRandom()
    return _sample_geometric(q, rng=rng) - _sample_geometric(q, rng=rng)


def _sample_geometric(q: float, *, rng: random.Random) -> int:
    # P(G = k) = (1-q) q^k on k >= 0.
    u = rng.random()
    if not _is_probability_sample(u):
        raise ReleaseCardError("rng.random() must return a finite value in [0, 1)")
    if u <= 0:
        return 0
    return int(math.floor(math.log1p(-u) / math.log(q)))


def _is_probability_sample(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and 0 <= value < 1
    )


def _is_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )
