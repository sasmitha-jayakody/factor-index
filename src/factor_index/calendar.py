"""Review calendar.

Semi-annual index reviews follow the standard provider sequence:

* **Cut-off date** — last trading day of February / August. All eligibility
  and factor data are taken as of this date (point-in-time).
* **Announcement date** — 10 business days before the effective date
  (informational; not used by the engine, but part of a real methodology).
* **Effective date** — the review is implemented after the close of the third
  Friday of March / September; new constituents and weights apply from the
  open of the next trading day.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ReviewEvent:
    cutoff: pd.Timestamp        # data as-of date
    announcement: pd.Timestamp
    effective: pd.Timestamp     # rebalance implemented after this close


class ReviewCalendar:
    """Builds the review schedule over a trading-day index."""

    def __init__(self, trading_days: pd.DatetimeIndex,
                 review_months: tuple[int, ...] = (3, 9)):
        self.trading_days = trading_days
        self.review_months = review_months

    @staticmethod
    def _third_friday(year: int, month: int) -> pd.Timestamp:
        d = pd.Timestamp(year=year, month=month, day=1)
        fridays = pd.date_range(d, d + pd.offsets.MonthEnd(0), freq="W-FRI")
        return fridays[2]

    def _last_trading_day_on_or_before(self, ts: pd.Timestamp) -> pd.Timestamp:
        pos = self.trading_days.searchsorted(ts, side="right") - 1
        return self.trading_days[pos]

    def schedule(self) -> list[ReviewEvent]:
        events: list[ReviewEvent] = []
        years = range(self.trading_days[0].year, self.trading_days[-1].year + 1)
        for yr in years:
            for m in self.review_months:
                nominal_eff = self._third_friday(yr, m)
                nominal_cutoff = pd.Timestamp(yr, m, 1) - pd.Timedelta(days=1)
                # Both nominal dates must fall inside the data window. Without
                # this guard the searchsorted snap-back below silently clamps a
                # future review onto the last available trading day, producing a
                # phantom event whose cut-off, announcement and effective dates
                # all collapse onto the same date.
                if not (self.trading_days[0] <= nominal_cutoff
                        and nominal_eff <= self.trading_days[-1]):
                    continue
                eff = self._last_trading_day_on_or_before(nominal_eff)
                cutoff = self._last_trading_day_on_or_before(nominal_cutoff)
                ann = self._last_trading_day_on_or_before(
                    eff - pd.offsets.BDay(10))
                if cutoff >= self.trading_days[0] + pd.Timedelta(days=200):
                    events.append(ReviewEvent(cutoff, ann, eff))
        return events
