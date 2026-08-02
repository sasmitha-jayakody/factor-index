"""Divisor-based index calculation engine (Ground Rules §7-8).

Index arithmetic
----------------
The price index is the classic Laspeyres divisor form:

    PI_t = ( sum_i  n_i,t * p_i,t ) / D_t

where ``n_i,t`` is the number of index shares of constituent i (fixed between
events) and ``D_t`` the divisor. Any event that changes basket market value
without a market price move (deletions, review rebalances) triggers a divisor
adjustment **after the close** of day t-1:

    D_t = D_{t-1} * MV_{t-1}(new basket) / MV_{t-1}(old basket)

so the index level is continuous through the event.

Corporate action treatment
--------------------------
* **Share split (r-for-1)** - index shares multiplied by r at the open of the
  ex-date; price drops mechanically; basket MV unchanged; **no divisor
  change**; price and total-return index both unaffected.
* **Ordinary cash dividend** - price index unaffected; the total-return index
  reinvests the dividend amount across the whole basket on the ex-date.
* **Deletion (delisting / failure)** - removed at its last available close;
  divisor adjusted; no intra-review replacement (next review restores count).
* **Review rebalance** - new basket set from target weights at the effective
  date close; new index shares n_i = w_i * MV_eff / p_i,eff, which preserves
  MV and therefore requires no divisor change by construction.

The engine is weighting-agnostic: it receives a ``select_and_weight``
callable, so the factor index and its cap-weighted benchmark run through the
IDENTICAL calculation path - differences in results are attributable to
methodology, not implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from .calendar import ReviewCalendar, ReviewEvent
from .universe import MarketData

# select_and_weight(data, cutoff) -> target weights indexed by security_id
WeightFn = Callable[[MarketData, pd.Timestamp], pd.Series]


@dataclass
class IndexResult:
    price_index: pd.Series
    total_return_index: pd.Series
    constituents: dict[pd.Timestamp, pd.Series]   # effective date -> target w
    review_turnover: pd.Series                    # two-way turnover per review
    review_log: pd.DataFrame                      # audit trail
    daily_weights_sample: dict = field(default_factory=dict)


class IndexEngine:
    def __init__(self, data: MarketData, calendar: ReviewCalendar,
                 select_and_weight: WeightFn, name: str = "INDEX"):
        self.data = data
        self.calendar = calendar
        self.select_and_weight = select_and_weight
        self.name = name

    # ------------------------------------------------------------------ #
    def run(self, base_value: float = 1000.0) -> IndexResult:
        d = self.data
        dates = d.dates
        px = d.prices.to_numpy()
        splits = d.split_factor.to_numpy()
        divs = d.dividends.to_numpy()
        n_sec = px.shape[1]
        col_of = {s: j for j, s in enumerate(d.securities)}

        events: list[ReviewEvent] = self.calendar.schedule()
        if not events:
            raise ValueError("no review events inside the data window")
        eff_by_pos = {int(dates.searchsorted(e.effective)): e for e in events}

        # ---- initialise at the first review effective date ---------------
        first_eff_pos = min(eff_by_pos)
        n = np.zeros(n_sec)                       # index shares
        divisor = np.nan
        pi = np.full(len(dates), np.nan)
        tr = np.full(len(dates), np.nan)

        constituents: dict[pd.Timestamp, pd.Series] = {}
        turnover_rows, log_rows = [], []

        start = first_eff_pos
        e0 = eff_by_pos[start]
        w0 = self.select_and_weight(d, e0.cutoff)
        n = self._shares_from_weights(w0, px[start], col_of, basket_mv=base_value)
        divisor = float(np.nansum(n * px[start]) / base_value)
        pi[start] = tr[start] = base_value
        constituents[e0.effective] = w0
        log_rows.append((e0.effective, len(w0), np.nan, "inception"))

        # ---- daily loop ---------------------------------------------------
        for t in range(start + 1, len(dates)):
            prev_mv_old = np.nansum(n * px[t - 1])

            # (1) deletions: constituent with no price today -> remove at
            #     yesterday's close, adjust divisor (after close of t-1).
            gone = (n > 0) & np.isnan(px[t])
            if gone.any():
                n[gone] = 0.0
                mv_new = np.nansum(n * px[t - 1])
                divisor *= mv_new / prev_mv_old
                prev_mv_old = mv_new

            # (2) splits at the open of t: n scales, MV unchanged, no divisor
            #     change. prev-close MV stays on the OLD share basis, which is
            #     consistent because r-for-1 split leaves n*p invariant.
            sf = splits[t]
            has_split = (n > 0) & (sf != 1.0)
            if has_split.any():
                n[has_split] *= sf[has_split]

            # (3) index levels
            mv_t = np.nansum(n * px[t])
            div_cash = np.nansum(n * np.nan_to_num(divs[t]))
            pi[t] = mv_t / divisor
            tr[t] = tr[t - 1] * (mv_t + div_cash) / prev_mv_old

            # (4) review effective after today's close
            if t in eff_by_pos:
                ev = eff_by_pos[t]
                w_tgt = self.select_and_weight(d, ev.cutoff)
                # drop anything that died between cut-off and effective date
                priced = w_tgt.index[[np.isfinite(px[t][col_of[s]])
                                      for s in w_tgt.index]]
                w_tgt = w_tgt.loc[priced]
                w_tgt = w_tgt / w_tgt.sum()

                w_drift = self._current_weights(n, px[t], d.securities)
                two_way = 0.5 * float(
                    (w_tgt.reindex(d.securities, fill_value=0.0)
                     - w_drift).abs().sum())

                n = self._shares_from_weights(w_tgt, px[t], col_of,
                                              basket_mv=mv_t)
                divisor = float(np.nansum(n * px[t]) / pi[t])
                constituents[ev.effective] = w_tgt
                turnover_rows.append((ev.effective, two_way))
                log_rows.append((ev.effective, len(w_tgt), two_way,
                                 f"review cutoff={ev.cutoff.date()}"))

        idx = dates
        turnover = (pd.Series(dict(turnover_rows), name="two_way_turnover")
                    if turnover_rows else pd.Series(dtype=float))
        log = pd.DataFrame(log_rows, columns=["effective", "n_constituents",
                                              "two_way_turnover", "note"])
        return IndexResult(
            price_index=pd.Series(pi, index=idx, name=f"{self.name}_PI").dropna(),
            total_return_index=pd.Series(tr, index=idx,
                                         name=f"{self.name}_TR").dropna(),
            constituents=constituents,
            review_turnover=turnover,
            review_log=log,
        )

    # ------------------------------------------------------------------ #
    @staticmethod
    def _shares_from_weights(w: pd.Series, px_row: np.ndarray,
                             col_of: dict, basket_mv: float) -> np.ndarray:
        n = np.zeros(len(col_of))
        for s, wi in w.items():
            j = col_of[s]
            p = px_row[j]
            if np.isfinite(p) and p > 0:
                n[j] = wi * basket_mv / p
        return n

    @staticmethod
    def _current_weights(n: np.ndarray, px_row: np.ndarray,
                         securities: pd.Index) -> pd.Series:
        mv = n * np.nan_to_num(px_row)
        total = mv.sum()
        return pd.Series(mv / total if total > 0 else mv, index=securities)
