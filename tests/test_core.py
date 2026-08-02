"""Sanity tests for the index engine's core guarantees.

Run:  python -m pytest tests/ -q
"""

import numpy as np
import pandas as pd
import pytest

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from factor_index.weighting import apply_capping, tilt_weights
from factor_index.calendar import ReviewCalendar
from factor_index.universe import MarketData
from factor_index.engine import IndexEngine


# ---------------------------------------------------------------- capping
def test_capping_respects_cap_and_sums_to_one():
    rng = np.random.default_rng(0)
    w = pd.Series(rng.pareto(1.5, 100) + 0.01,
                  index=[f"S{i}" for i in range(100)])
    w /= w.sum()
    capped = apply_capping(w, cap=0.05)
    assert capped.max() <= 0.05 + 1e-9
    assert abs(capped.sum() - 1.0) < 1e-9
    # ordering among uncapped names preserved
    free = capped[capped < 0.05 - 1e-9]
    orig = w.loc[free.index]
    assert (free.sort_values().index == orig.sort_values().index).all()


def test_capping_infeasible_raises():
    w = pd.Series([0.5, 0.5], index=["A", "B"])
    with pytest.raises(ValueError):
        apply_capping(w, cap=0.3)  # 2 x 0.3 < 1


def test_tilt_weights_normalised():
    mcap = pd.Series([100.0, 200.0, 50.0], index=list("ABC"))
    score = pd.Series([0.9, 0.1, 0.5], index=list("ABC"))
    w = tilt_weights(mcap, score)
    assert abs(w.sum() - 1.0) < 1e-12
    assert w["A"] > w["B"]  # tilt overcomes mcap here: 90 vs 20


# ---------------------------------------------------------------- calendar
def test_third_friday():
    assert ReviewCalendar._third_friday(2024, 3) == pd.Timestamp("2024-03-15")
    assert ReviewCalendar._third_friday(2025, 9) == pd.Timestamp("2025-09-19")


def test_no_phantom_review_past_end_of_data():
    """A review whose nominal dates fall outside the window must not be emitted.

    History ends 2025-06-30, so the September 2025 review does not exist. It
    must not be clamped back onto the final trading day.
    """
    dates = pd.bdate_range("2010-01-04", "2025-06-30")
    events = ReviewCalendar(dates).schedule()
    assert events[-1].effective == pd.Timestamp("2025-03-21")
    for e in events:
        assert e.cutoff < e.announcement < e.effective
        assert e.effective <= dates[-1]


# ------------------------------------------------------- engine invariants
def _tiny_market(px: np.ndarray, splits: np.ndarray | None = None,
                 divs: np.ndarray | None = None) -> MarketData:
    T, N = px.shape
    dates = pd.bdate_range("2020-01-01", periods=T)
    ids = pd.Index([f"S{i}" for i in range(N)], name="security_id")
    ones = np.ones_like(px)
    M = lambda a: pd.DataFrame(a, index=dates, columns=ids)  # noqa: E731
    fund = pd.DataFrame({
        "security_id": list(ids), "report_date": [dates[0]] * N,
        "eps_ttm_adj": 1.0, "bvps_adj": 5.0, "roe": 0.1,
        "debt_to_assets": 0.3, "eps_var": 0.2})
    return MarketData(
        prices=M(px), shares_outstanding=M(ones * 1e6), free_float=M(ones),
        split_factor=M(splits if splits is not None else ones),
        dividends=M(divs if divs is not None else np.zeros_like(px)),
        volume=M(ones * 1e9), fundamentals=fund,
        sectors=pd.Series("Tech", index=ids))


class _EqualWeight:
    def __call__(self, data, cutoff):
        t = data.dates.searchsorted(cutoff, side="right") - 1
        live = data.prices.iloc[t].dropna().index
        return pd.Series(1.0 / len(live), index=live)


class _Cal:
    """Single inception review at a fixed position."""
    def __init__(self, dates, pos=0):
        from factor_index.calendar import ReviewEvent
        self._ev = [ReviewEvent(dates[pos], dates[pos], dates[pos])]
    def schedule(self):
        return self._ev


def test_split_leaves_index_unchanged():
    """A 2-for-1 split with no price move must not move the index."""
    T, N = 6, 3
    px = np.full((T, N), 100.0)
    splits = np.ones((T, N))
    splits[3, 0] = 2.0
    px[3:, 0] = 50.0                       # mechanical halving, no real move
    data = _tiny_market(px, splits=splits)
    res = IndexEngine(data, _Cal(data.dates), _EqualWeight()).run(1000.0)
    assert np.allclose(res.price_index.values, 1000.0)
    assert np.allclose(res.total_return_index.values, 1000.0)


def test_deletion_divisor_continuity():
    """Deleting a flat-priced stock must not jump the index."""
    T, N = 6, 3
    px = np.full((T, N), 100.0)
    px[3:, 2] = np.nan                     # delists after day 2
    data = _tiny_market(px)
    res = IndexEngine(data, _Cal(data.dates), _EqualWeight()).run(1000.0)
    assert np.allclose(res.price_index.values, 1000.0)


def test_dividend_lifts_tr_not_pi():
    T, N = 4, 2
    px = np.full((T, N), 100.0)
    divs = np.zeros((T, N))
    divs[2, :] = 1.0                       # 1% yield on ex-date
    data = _tiny_market(px, divs=divs)
    res = IndexEngine(data, _Cal(data.dates), _EqualWeight()).run(1000.0)
    assert np.allclose(res.price_index.values, 1000.0)
    assert res.total_return_index.iloc[-1] == pytest.approx(1010.0)
