"""Backtest analytics (performance, risk, turnover, cost drag)."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def daily_returns(level: pd.Series) -> pd.Series:
    return level.pct_change().dropna()


def annualized_return(level: pd.Series) -> float:
    yrs = (level.index[-1] - level.index[0]).days / 365.25
    return float((level.iloc[-1] / level.iloc[0]) ** (1.0 / yrs) - 1.0)


def annualized_vol(level: pd.Series) -> float:
    return float(daily_returns(level).std(ddof=1) * np.sqrt(TRADING_DAYS))


def max_drawdown(level: pd.Series) -> float:
    dd = level / level.cummax() - 1.0
    return float(dd.min())


def drawdown_series(level: pd.Series) -> pd.Series:
    return level / level.cummax() - 1.0


def tracking_error(level: pd.Series, bench: pd.Series) -> float:
    a = daily_returns(level).align(daily_returns(bench), join="inner")
    active = a[0] - a[1]
    return float(active.std(ddof=1) * np.sqrt(TRADING_DAYS))


def information_ratio(level: pd.Series, bench: pd.Series) -> float:
    te = tracking_error(level, bench)
    if te == 0:
        return np.nan
    er = annualized_return(level) - annualized_return(bench)
    return float(er / te)


def active_return_tstat(level: pd.Series, bench: pd.Series) -> float:
    a = daily_returns(level).align(daily_returns(bench), join="inner")
    active = (a[0] - a[1]).dropna()
    return float(active.mean() / active.std(ddof=1) * np.sqrt(len(active)))


def cost_drag_annual(review_turnover: pd.Series, bps_per_unit: float = 15.0,
                     reviews_per_year: float = 2.0) -> float:
    """Approximate annual cost drag: two-way turnover x cost per unit traded.

    ``bps_per_unit`` is round-trip cost in basis points per 100% two-way
    turnover (spread + impact for liquid large caps ~10-20bp).
    """
    if review_turnover.empty:
        return 0.0
    avg = float(review_turnover.mean())
    return avg * (bps_per_unit / 1e4) * reviews_per_year


def summary_table(levels: dict[str, pd.Series],
                  bench_key: str,
                  turnovers: dict[str, pd.Series] | None = None,
                  rf: float = 0.0) -> pd.DataFrame:
    rows = {}
    bench = levels[bench_key]
    for name, lv in levels.items():
        r = {
            "Ann. return": annualized_return(lv),
            "Ann. vol": annualized_vol(lv),
            "Sharpe (rf=0)": (annualized_return(lv) - rf) / annualized_vol(lv),
            "Max drawdown": max_drawdown(lv),
        }
        if name != bench_key:
            r["Active return"] = annualized_return(lv) - annualized_return(bench)
            r["Tracking error"] = tracking_error(lv, bench)
            r["Information ratio"] = information_ratio(lv, bench)
            r["Active t-stat"] = active_return_tstat(lv, bench)
        if turnovers and name in turnovers and not turnovers[name].empty:
            r["Avg review turnover (2-way)"] = float(turnovers[name].mean())
            r["Est. cost drag p.a. (15bp)"] = cost_drag_annual(turnovers[name])
        rows[name] = r
    return pd.DataFrame(rows)
