"""Concrete index methodologies wired for the engine.

Both the factor index and its benchmark are expressed as
``select_and_weight(data, cutoff) -> weights`` callables and run through the
identical engine, so performance differences are attributable to methodology
alone.
"""

from __future__ import annotations

import pandas as pd

from .eligibility import EligibilityParams, apply_eligibility_screens
from .factors import composite_factor_scores
from .universe import MarketData
from .weighting import apply_capping, tilt_weights


def _ff_mcap(data: MarketData, cutoff: pd.Timestamp,
             securities: pd.Index) -> pd.Series:
    t = data.dates.searchsorted(cutoff, side="right") - 1
    px = data.prices.iloc[t].reindex(securities)
    sh = data.shares_outstanding.iloc[t].reindex(securities)
    ff = data.free_float.iloc[t].reindex(securities)
    return px * sh * ff


class QualityValueIndex:
    """SJFI Quality-Value tilt index: Ground Rules §§3–5."""

    def __init__(self, elig: EligibilityParams = EligibilityParams(),
                 cap: float = 0.05):
        self.elig = elig
        self.cap = cap
        self.review_diagnostics: dict[pd.Timestamp, pd.DataFrame] = {}

    def __call__(self, data: MarketData, cutoff: pd.Timestamp) -> pd.Series:
        screens = apply_eligibility_screens(data, cutoff, self.elig)
        eligible = screens.index[screens["eligible"]]
        scores = composite_factor_scores(data, cutoff, eligible)
        mcap = _ff_mcap(data, cutoff, eligible)
        w = tilt_weights(mcap, scores["score"])
        w = apply_capping(w, cap=self.cap)
        diag = scores.copy()
        diag["ff_mcap"] = mcap
        diag["weight"] = w
        self.review_diagnostics[cutoff] = diag
        return w


class CapWeightedBenchmark:
    """Free-float market-cap-weighted parent benchmark on the same
    eligible universe (no factor tilt, no cap)."""

    def __init__(self, elig: EligibilityParams = EligibilityParams()):
        self.elig = elig

    def __call__(self, data: MarketData, cutoff: pd.Timestamp) -> pd.Series:
        screens = apply_eligibility_screens(data, cutoff, self.elig)
        eligible = screens.index[screens["eligible"]]
        mcap = _ff_mcap(data, cutoff, eligible)
        return mcap / mcap.sum()
