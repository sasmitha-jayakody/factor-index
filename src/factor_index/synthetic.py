"""Synthetic universe generator.

Produces a point-in-time-correct ``MarketData`` object for N securities over a
multi-year daily history, with:

* a linear factor structure in returns (market + sector + value + quality +
  idiosyncratic), with modest embedded value/quality premia so a factor-index
  backtest is illustrative rather than degenerate;
* quarterly fundamentals (E/P, B/P inputs, ROE, leverage, EPS variability)
  noisily correlated with each security's true loadings, published with a
  45-day reporting lag (point-in-time, look-ahead safe);
* corporate actions: quarterly cash dividends, share splits, mid-sample
  delistings and IPOs.

This module exists ONLY because the build environment has no market-data
access. The engine never imports it; any adapter that returns ``MarketData``
(CRSP, LSEG/Refinitiv, yfinance) drives everything downstream unchanged.

Per-share fundamentals are stored on the FIRST-DAY share basis (i.e. fully
split-adjusted back to the start of the sample). The factor module converts
review-date unadjusted prices onto the same basis via the cumulative split
factor, so ratios are always computed on a consistent basis.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .universe import MarketData

SECTORS = ["Energy", "Materials", "Industrials", "Cons Disc", "Cons Staples",
           "Health Care", "Financials", "Technology", "Telecom", "Utilities"]

TRADING_DAYS = 252


def generate_universe(
    n_securities: int = 500,
    start: str = "2010-01-04",
    end: str = "2025-06-30",
    seed: int = 7,
    value_premium_annual: float = 0.020,
    quality_premium_annual: float = 0.015,
    market_premium_annual: float = 0.055,
) -> MarketData:
    """Generate a synthetic investable universe. See module docstring."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, end)
    T, N = len(dates), n_securities
    ids = pd.Index([f"SEC{i:04d}" for i in range(N)], name="security_id")

    # ---- static characteristics ------------------------------------------
    sectors = pd.Series(rng.choice(SECTORS, size=N), index=ids, name="sector")
    beta = rng.normal(1.0, 0.25, N).clip(0.3, 1.9)
    load_val = rng.normal(0.0, 1.0, N)                 # true value loading
    load_qual = rng.normal(0.0, 1.0, N)                # true quality loading
    idio_vol = rng.uniform(0.18, 0.45, N) / np.sqrt(TRADING_DAYS)

    # ---- listing windows: IPOs and delistings ----------------------------
    first_idx = np.zeros(N, dtype=int)
    ipo = rng.random(N) < 0.15
    first_idx[ipo] = rng.integers(60, T - 400, ipo.sum())
    last_idx = np.full(N, T - 1, dtype=int)
    for i in np.where(rng.random(N) < 0.12)[0]:
        lo = first_idx[i] + 300
        if lo < T - 60:
            last_idx[i] = rng.integers(lo, T - 30)

    # ---- daily returns with embedded premia ------------------------------
    mkt = rng.normal(market_premium_annual / TRADING_DAYS,
                     0.16 / np.sqrt(TRADING_DAYS), T)
    sec_ret = rng.normal(0.0, 0.05 / np.sqrt(TRADING_DAYS), (T, len(SECTORS)))
    f_val = rng.normal(value_premium_annual / TRADING_DAYS,
                       0.04 / np.sqrt(TRADING_DAYS), T)
    f_qual = rng.normal(quality_premium_annual / TRADING_DAYS,
                        0.03 / np.sqrt(TRADING_DAYS), T)
    sector_col = np.array([SECTORS.index(s) for s in sectors])
    rets = (beta * mkt[:, None]
            + sec_ret[:, sector_col]
            + 0.30 * load_val[None, :] * f_val[:, None]
            + 0.25 * load_qual[None, :] * f_qual[:, None]
            + rng.normal(0.0, 1.0, (T, N)) * idio_vol)

    # ---- prices: adjusted path first, then overlay splits ----------------
    p0 = np.exp(rng.normal(3.4, 0.9, N)).clip(2.0, 400.0)
    adj_px = np.exp(np.log(p0)[None, :] + np.cumsum(np.log1p(rets), axis=0))

    split_factor = np.ones((T, N))
    for i in range(N):
        for _ in range(rng.poisson(0.35)):
            lo, hi = first_idx[i] + 120, last_idx[i] - 5
            if hi > lo:
                t = rng.integers(lo, hi)
                split_factor[t, i] *= rng.choice([2.0, 3.0], p=[0.85, 0.15])
    cum_split = np.cumprod(split_factor, axis=0)       # shares multiplier
    unadj_px = adj_px / cum_split                      # as-traded price

    # ---- shares outstanding and free float -------------------------------
    base_shares = np.exp(rng.normal(18.0, 1.1, N))
    shares = base_shares[None, :] * cum_split
    ff = np.tile(rng.beta(5, 1.6, N).clip(0.02, 1.0), (T, 1))

    # ---- quarterly cash dividends (ex-date = 10th b.day of Mar/Jun/Sep/Dec)
    div_yield = np.clip(rng.normal(0.022 + 0.004 * load_val, 0.012), 0.0, 0.06)
    dividends = np.zeros((T, N))
    for q_m in (3, 6, 9, 12):
        for yr in np.unique(dates.year):
            sel = np.where((dates.year == yr) & (dates.month == q_m))[0]
            if len(sel) >= 10:
                t = sel[9]
                dividends[t, :] = unadj_px[t, :] * div_yield / 4.0

    # ---- traded value for liquidity screens ------------------------------
    turnover_rate = rng.uniform(0.001, 0.01, N)
    volume = (unadj_px * shares) * turnover_rate[None, :] \
        * rng.lognormal(0.0, 0.5, (T, N))

    # ---- listing mask ------------------------------------------------------
    alive = np.zeros((T, N), dtype=bool)
    for i in range(N):
        alive[first_idx[i]: last_idx[i] + 1, i] = True
    unadj_px = np.where(alive, unadj_px, np.nan)
    shares = np.where(alive, shares, np.nan)
    ff = np.where(alive, ff, np.nan)
    volume = np.where(alive, volume, np.nan)
    dividends = np.where(alive, dividends, 0.0)

    # ---- point-in-time fundamentals (45-day lag) --------------------------
    rows = []
    for qi, q_end in enumerate(pd.date_range(dates[0], dates[-1], freq="QE")):
        t = int(dates.searchsorted(q_end, side="right")) - 1
        if t < 0:
            continue
        pub = q_end + pd.Timedelta(days=45)
        rq = np.random.default_rng(seed + 1000 + qi)
        ep = np.clip(0.055 + 0.020 * load_val + rq.normal(0, 0.015, N), 0.005, 0.25)
        bp = np.clip(0.50 + 0.18 * load_val + rq.normal(0, 0.12, N), 0.05, 2.50)
        roe = np.clip(0.11 + 0.05 * load_qual + rq.normal(0, 0.03, N), -0.10, 0.45)
        d2a = np.clip(0.32 - 0.07 * load_qual + rq.normal(0, 0.06, N), 0.00, 0.90)
        evar = np.clip(0.20 - 0.06 * load_qual + rq.normal(0, 0.05, N), 0.02, 0.80)
        for i in range(N):
            if alive[t, i]:
                # per-share values on first-day share basis (adjusted basis)
                rows.append((ids[i], pub,
                             ep[i] * adj_px[t, i], bp[i] * adj_px[t, i],
                             roe[i], d2a[i], evar[i]))
    fundamentals = pd.DataFrame(rows, columns=[
        "security_id", "report_date", "eps_ttm_adj", "bvps_adj",
        "roe", "debt_to_assets", "eps_var"])

    def M(a: np.ndarray) -> pd.DataFrame:
        return pd.DataFrame(a, index=dates, columns=ids)

    return MarketData(
        prices=M(unadj_px),
        shares_outstanding=M(shares),
        free_float=M(ff),
        split_factor=M(split_factor),
        dividends=M(dividends),
        volume=M(volume),
        fundamentals=fundamentals,
        sectors=sectors,
        meta={"seed": seed, "true_value_loading": pd.Series(load_val, index=ids),
              "true_quality_loading": pd.Series(load_qual, index=ids)},
    )
