"""pass@k, pass@1, and pass^k metrics.

- `pass_at_k` uses the Chen et al. 2021 unbiased estimator:
      pass@k = 1 - C(n-c, k) / C(n, k)
  computed in log space to avoid combinatorial overflow.
- `pass^k` = fraction of tasks for which all k seeds passed (TAU-Bench
  reliability, Yao et al. 2024).
- Both operate on a per-task pass-count distribution.

See docs/metrics.md §1.1 for adversarial considerations.
"""

from __future__ import annotations

import math
from typing import Sequence


def pass_at_k(n: int, c: int, k: int) -> float:
    """Chen et al. 2021 unbiased estimator.

    Args:
        n: total samples drawn.
        c: number of samples that passed.
        k: the k in pass@k. Must satisfy 0 < k <= n.

    Returns:
        Probability in [0, 1] that at least one of k samples drawn (without
        replacement) from the n samples would have passed.
    """
    if not (0 < k <= n):
        raise ValueError(f"require 0 < k <= n, got n={n}, k={k}")
    if c < 0 or c > n:
        raise ValueError(f"require 0 <= c <= n, got n={n}, c={c}")
    if c == 0:
        return 0.0
    if c == n:
        return 1.0
    if k > n - c:
        # Definitely at least one correct — the binomial is 0.
        return 1.0
    # Use log-space to handle large n.
    log_comb_top = _log_comb(n - c, k)
    log_comb_bot = _log_comb(n, k)
    return 1.0 - math.exp(log_comb_top - log_comb_bot)


def pass_at_1(per_task_pass_counts: Sequence[int], n_seeds: int) -> float:
    """Run-level pass@1 = average per-task probability of passing on seed 1.

    With canonical seeds this is exactly `mean(seed_1_passed)` across tasks.
    For the general estimator form, we use c/n at k=1 which equals c/n.
    """
    if not per_task_pass_counts:
        return 0.0
    return sum(pass_at_k(n_seeds, c, 1) for c in per_task_pass_counts) / len(
        per_task_pass_counts
    )


def pass_caret_k(per_task_pass_counts: Sequence[int], k: int) -> float:
    """TAU-Bench pass^k: fraction of tasks where ALL k samples passed.

    With canonical 5-seed runs, `pass^5` is `mean(c == 5)`.
    """
    if not per_task_pass_counts:
        return 0.0
    return sum(1 for c in per_task_pass_counts if c >= k) / len(per_task_pass_counts)


def _log_comb(n: int, k: int) -> float:
    """log(C(n, k)) via lgamma; supports large n."""
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
