"""Factor definitions and scoring (Ground Rules §4).

Value composite (equal-weight of z-scores):
    * Earnings yield  E/P  (trailing 12m EPS / price)
    * Book-to-price   B/P

Quality composite (equal-weight of z-scores):
    * Return on equity            (higher is better)
    * Leverage: debt-to-assets    (lower is better, sign-flipped)
    * Earnings variability        (lower is better, sign-flipped)

Scoring pipeline, evaluated on the ELIGIBLE universe at the review cut-off:

1. Compute raw ratios on a consistent share basis. Per-share fundamentals are
   stored split-adjusted to the first sample day; the cut-off price is put on
   the same basis via the cumulative split factor.
2. Cross-sectional z-scores, winsorized at +/- 3.
3. Composite z = mean of available component z-scores (min 1 per pillar).
4. Map each pillar composite to a tilt score in (0, 1) via the standard
   normal CDF:  S = Phi(z).  The final security score is
   S_value * S_quality  (a "sequential tilt" / multiplicative tilt, the
   standard multi-factor tilt construction).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from .universe import MarketData

WINSOR = 3.0


def _zscore(s: pd.Series) -> pd.Series:
    mu, sd = s.mean(), s.std(ddof=0)
    if not np.isfinite(sd) or sd == 0:
        return pd.Series(0.0, index=s.index)
    return ((s - mu) / sd).clip(-WINSOR, WINSOR)


def composite_factor_scores(
    data: MarketData,
    cutoff: pd.Timestamp,
    eligible: pd.Index,
) -> pd.DataFrame:
    """Return per-security factor diagnostics and the final tilt score.

    Output columns: z_value, z_quality, s_value, s_quality, score.
    Only securities in `eligible` are scored; z-scores are computed within
    that set (the correct peer group - scoring against ineligible names
    contaminates the cross-section).
    """
    t = data.dates.searchsorted(cutoff, side="right") - 1
    px = data.prices.iloc[t].reindex(eligible)
    cum_split = data.split_factor.iloc[: t + 1].prod().reindex(eligible)
    adj_px = px * cum_split  # price on first-day share basis

    fund = data.fundamentals_asof(cutoff).reindex(eligible)

    ep = fund["eps_ttm_adj"] / adj_px
    bp = fund["bvps_adj"] / adj_px
    z_value = pd.concat([_zscore(ep), _zscore(bp)], axis=1).mean(axis=1)

    z_quality = pd.concat([
        _zscore(fund["roe"]),
        _zscore(-fund["debt_to_assets"]),
        _zscore(-fund["eps_var"]),
    ], axis=1).mean(axis=1)

    s_value = pd.Series(norm.cdf(z_value), index=eligible)
    s_quality = pd.Series(norm.cdf(z_quality), index=eligible)

    return pd.DataFrame({
        "z_value": z_value, "z_quality": z_quality,
        "s_value": s_value, "s_quality": s_quality,
        "score": s_value * s_quality,
    })
