"""Bootstrap CI implementation.

Per docs/metrics.md §3: resample with replacement (tasks for capability
metrics, (task, seed) pairs for efficiency metrics), recompute the metric,
take the empirical 2.5th and 97.5th percentiles over 10 000 iterations.
"""

from __future__ import annotations

import math
from typing import Callable, Sequence, TypeVar

try:
    import numpy as np  # type: ignore[import-not-found]
    _NUMPY = True
except ImportError:  # pragma: no cover
    _NUMPY = False

T = TypeVar("T")

DEFAULT_ITERATIONS = 10_000
DEFAULT_CI = 0.95


def bootstrap_ci(
    samples: Sequence[T],
    statistic: Callable[[Sequence[T]], float],
    *,
    iterations: int = DEFAULT_ITERATIONS,
    ci: float = DEFAULT_CI,
    seed: int = 42,
) -> tuple[float, float]:
    """Bootstrap (lo, hi) for `statistic(samples)`.

    `samples` is resampled with replacement; `statistic` is evaluated on each
    resample. Returns the (ci/2, 1 - ci/2) percentiles of the bootstrap
    distribution.
    """
    if not samples:
        return (0.0, 0.0)
    n = len(samples)
    alpha = (1.0 - ci) / 2.0

    if _NUMPY:
        rng = np.random.default_rng(seed)
        idx = rng.integers(0, n, size=(iterations, n))
        # Resample and compute statistic; statistic operates on the resampled list.
        # We accept the Python-call overhead because statistics aren't necessarily
        # vectorisable (e.g., pass@k uses combinatorials).
        stats = np.empty(iterations, dtype=float)
        sample_list = list(samples)
        for i in range(iterations):
            resample = [sample_list[j] for j in idx[i]]
            stats[i] = float(statistic(resample))
        lo = float(np.quantile(stats, alpha))
        hi = float(np.quantile(stats, 1.0 - alpha))
        return (lo, hi)

    # Pure-stdlib fallback (slow). Used if numpy isn't installed.
    import random

    rng = random.Random(seed)
    sample_list = list(samples)
    stats: list[float] = []
    for _ in range(iterations):
        resample = [rng.choice(sample_list) for _ in range(n)]
        stats.append(float(statistic(resample)))
    stats.sort()
    lo = stats[int(math.floor(alpha * iterations))]
    hi = stats[min(iterations - 1, int(math.ceil((1.0 - alpha) * iterations)) - 1)]
    return (lo, hi)


def bootstrap_proportion_ci(
    n_successes: int,
    n_total: int,
    *,
    ci: float = DEFAULT_CI,
) -> tuple[float, float]:
    """Wilson interval for a binomial proportion (used for timeout_rate).

    Faster + tighter than bootstrap for a single proportion; matches
    docs/metrics.md §1.2 `timeout_rate`.
    """
    if n_total == 0:
        return (0.0, 0.0)
    alpha = 1.0 - ci
    # z-score for two-tailed alpha.
    z = _z_for_alpha(alpha / 2.0)
    p = n_successes / n_total
    denom = 1.0 + z * z / n_total
    center = (p + z * z / (2.0 * n_total)) / denom
    half = (z * math.sqrt(p * (1.0 - p) / n_total + z * z / (4.0 * n_total**2))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def _z_for_alpha(alpha: float) -> float:
    """Inverse standard normal CDF; we hard-code 95% as 1.959964."""
    if abs(alpha - 0.025) < 1e-9:
        return 1.959964
    if abs(alpha - 0.005) < 1e-9:
        return 2.575829
    if abs(alpha - 0.05) < 1e-9:
        return 1.644854
    raise ValueError(f"unsupported alpha {alpha}")
