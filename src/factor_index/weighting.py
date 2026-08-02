"""Weighting and capping (Ground Rules §5).

Target weights at each review:

    w_i  proportional to  FreeFloatMcap_i x Score_i

subject to a single-constituent cap. Capping uses the standard iterative
redistribution algorithm: cap all breaching names at the limit, redistribute
the excess pro-rata across uncapped names, and repeat until no breaches
remain. The algorithm provably terminates (the capped set grows each
iteration) provided N x cap >= 1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def tilt_weights(ff_mcap: pd.Series, score: pd.Series) -> pd.Series:
    """Uncapped tilt weights: float-adjusted market cap x factor score."""
    raw = (ff_mcap * score).clip(lower=0.0)
    total = raw.sum()
    if total <= 0:
        raise ValueError("degenerate weight vector: all scores/mcaps <= 0")
    return raw / total


def apply_capping(weights: pd.Series, cap: float = 0.05,
                  max_iter: int = 200) -> pd.Series:
    """Iteratively cap weights at `cap` and redistribute pro-rata.

    Raises if capping is infeasible (N x cap < 1) or fails to converge.
    """
    w = weights / weights.sum()
    if len(w) * cap < 1.0 - 1e-12:
        raise ValueError(f"cap {cap} infeasible for {len(w)} constituents")
    capped_mask = pd.Series(False, index=w.index)
    for _ in range(max_iter):
        breach = (w > cap + 1e-12) & ~capped_mask
        if not breach.any():
            break
        capped_mask |= breach
        excess = (w[capped_mask] - cap).sum()
        w[capped_mask] = cap
        free = ~capped_mask
        if w[free].sum() <= 0:
            # everything capped: distribute equally among capped (edge case)
            w[:] = 1.0 / len(w)
            break
        w[free] += excess * w[free] / w[free].sum()
    else:
        raise RuntimeError("capping failed to converge")
    return w / w.sum()
