"""Eligibility screening (Ground Rules §3.2).

All screens are evaluated strictly on data available at the review cut-off.
A security must pass ALL screens to enter the eligible universe:

1. **Listing status** — traded (non-NaN price) on the cut-off date.
2. **Seasoning** — at least ``min_listing_days`` trading days of history.
3. **Free float** — free-float factor >= ``min_free_float``.
4. **Liquidity** — median daily traded value over the trailing 6 months
   >= ``min_mdtv``; and traded on >= 90% of days in that window.
5. **Price** — closing price >= ``min_price`` (penny-stock exclusion).
6. **Fundamental coverage** — a point-in-time fundamental record exists
   (a factor index cannot score a security it has no data for).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .universe import MarketData


@dataclass(frozen=True)
class EligibilityParams:
    min_listing_days: int = 126          # ~6 months seasoning
    min_free_float: float = 0.05
    min_mdtv: float = 1_000_000.0        # median daily traded value, 6m
    min_traded_share: float = 0.90       # fraction of days traded, 6m
    min_price: float = 1.0
    liquidity_window: int = 126


def apply_eligibility_screens(
    data: MarketData,
    cutoff: pd.Timestamp,
    params: EligibilityParams = EligibilityParams(),
) -> pd.DataFrame:
    """Return per-security screen results and overall eligibility at `cutoff`.

    Output: DataFrame indexed by security_id with one boolean column per
    screen plus ``eligible`` (AND of all screens). Keeping per-screen results
    makes review audit trails reproducible - a methodology requirement.
    """
    t = data.dates.searchsorted(cutoff, side="right") - 1
    if t < 0:
        raise ValueError("cutoff precedes data history")
    window = data.prices.iloc[max(0, t - params.liquidity_window + 1): t + 1]
    vol_window = data.volume.iloc[max(0, t - params.liquidity_window + 1): t + 1]

    px = data.prices.iloc[t]
    listed = px.notna()
    seasoned = data.prices.iloc[: t + 1].notna().sum() >= params.min_listing_days
    float_ok = data.free_float.iloc[t] >= params.min_free_float
    mdtv_ok = vol_window.median() >= params.min_mdtv
    traded_ok = window.notna().mean() >= params.min_traded_share
    price_ok = px >= params.min_price

    fund = data.fundamentals_asof(cutoff)
    coverage = pd.Series(data.securities.isin(fund.index), index=data.securities)

    out = pd.DataFrame({
        "listed": listed, "seasoned": seasoned, "free_float": float_ok,
        "liquidity_mdtv": mdtv_ok, "liquidity_traded": traded_ok,
        "min_price": price_ok, "fundamental_coverage": coverage,
    })
    out["eligible"] = out.all(axis=1)
    return out
