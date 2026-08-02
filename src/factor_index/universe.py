"""Market data container: the single boundary between data sources and the engine.

Any data source (synthetic, CRSP, LSEG/Refinitiv, yfinance) that can populate
a ``MarketData`` object can drive the index engine unchanged. All matrices are
(dates x securities) pandas DataFrames sharing a common trading-day
DatetimeIndex and security-ID columns. Prices are UNADJUSTED (as traded);
splits and dividends are supplied as separate event matrices, exactly as an
index provider receives them from a corporate-actions feed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class MarketData:
    """Unadjusted market and fundamental data for an investable universe.

    Attributes
    ----------
    prices : (T x N) unadjusted close prices; NaN before listing / after delisting.
    shares_outstanding : (T x N) total shares in issue (reflects splits).
    free_float : (T x N) free-float factor in [0, 1].
    split_factor : (T x N) split ratio effective at the open of that date
        (2.0 for a 2-for-1 split); 1.0 otherwise.
    dividends : (T x N) ordinary cash dividend per share, ex-date aligned.
    volume : (T x N) daily traded value in index currency (for liquidity screens).
    fundamentals : long-form DataFrame with columns
        [security_id, report_date, eps_ttm, bvps, roe, debt_to_assets, eps_var]
        where ``report_date`` is the first date the datum is PUBLIC (point-in-time,
        so screens are look-ahead safe).
    sectors : Series mapping security_id -> sector name.
    """

    prices: pd.DataFrame
    shares_outstanding: pd.DataFrame
    free_float: pd.DataFrame
    split_factor: pd.DataFrame
    dividends: pd.DataFrame
    volume: pd.DataFrame
    fundamentals: pd.DataFrame
    sectors: pd.Series
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        idx, cols = self.prices.index, self.prices.columns
        for name in ("shares_outstanding", "free_float", "split_factor",
                     "dividends", "volume"):
            m = getattr(self, name)
            if not (m.index.equals(idx) and m.columns.equals(cols)):
                raise ValueError(f"MarketData.{name} is not aligned with prices")

    @property
    def dates(self) -> pd.DatetimeIndex:
        return self.prices.index

    @property
    def securities(self) -> pd.Index:
        return self.prices.columns

    def fundamentals_asof(self, date: pd.Timestamp) -> pd.DataFrame:
        """Latest fundamental record per security that was public on/before `date`."""
        f = self.fundamentals[self.fundamentals["report_date"] <= date]
        return (f.sort_values("report_date")
                 .groupby("security_id", as_index=True)
                 .last())
