"""End-to-end backtest of the SJFI 500 Quality-Value Index vs its
cap-weighted parent benchmark, on the identical engine and universe.

Outputs (./outputs):
    summary_stats.csv         performance / risk / turnover table
    index_levels.csv          daily PI and TR levels for both indices
    review_log.csv            per-review audit trail
    backtest_report.png       4-panel chart
    factor_exposures.png      active factor exposure through time
"""

from __future__ import annotations

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))

from factor_index import ReviewCalendar, IndexEngine
from factor_index.analytics import drawdown_series, summary_table
from factor_index.strategies import CapWeightedBenchmark, QualityValueIndex
from factor_index.synthetic import generate_universe

OUT = pathlib.Path(__file__).resolve().parent / "outputs"
OUT.mkdir(exist_ok=True)


def main() -> None:
    print("Generating synthetic universe (500 securities, 2010-2025) ...")
    data = generate_universe(seed=4, market_premium_annual=0.065)
    cal = ReviewCalendar(data.dates)

    print("Running SJFI 500 Quality-Value Index ...")
    qv = QualityValueIndex(cap=0.05)
    res_qv = IndexEngine(data, cal, qv, name="SJFI_QV").run()

    print("Running cap-weighted parent benchmark ...")
    bench = CapWeightedBenchmark()
    res_bm = IndexEngine(data, cal, bench, name="PARENT_CW").run()

    # ---------------- tables -------------------------------------------
    levels = {"SJFI 500 Quality-Value (TR)": res_qv.total_return_index,
              "Parent Cap-Weighted (TR)": res_bm.total_return_index}
    stats = summary_table(levels, bench_key="Parent Cap-Weighted (TR)",
                          turnovers={"SJFI 500 Quality-Value (TR)":
                                     res_qv.review_turnover,
                                     "Parent Cap-Weighted (TR)":
                                     res_bm.review_turnover})
    stats.to_csv(OUT / "summary_stats.csv", float_format="%.4f")
    print("\n" + stats.round(4).to_string())

    pd.concat([res_qv.price_index, res_qv.total_return_index,
               res_bm.price_index, res_bm.total_return_index],
              axis=1).to_csv(OUT / "index_levels.csv", float_format="%.4f")
    res_qv.review_log.to_csv(OUT / "review_log.csv", index=False)

    # ---------------- 4-panel report chart -----------------------------
    tr_qv, tr_bm = res_qv.total_return_index, res_bm.total_return_index
    common = tr_qv.index.intersection(tr_bm.index)
    tr_qv, tr_bm = tr_qv.loc[common], tr_bm.loc[common]

    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5))
    fig.suptitle("SJFI 500 Quality-Value Index vs Cap-Weighted Parent "
                 "(synthetic universe)", fontsize=13)

    ax = axes[0, 0]
    ax.plot(tr_qv / tr_qv.iloc[0] * 1000, label="SJFI Quality-Value TR", lw=1.2)
    ax.plot(tr_bm / tr_bm.iloc[0] * 1000, label="Parent Cap-Weighted TR",
            lw=1.2, color="grey")
    ax.set_yscale("log"); ax.set_title("Total-return index (log scale)")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    ax = axes[0, 1]
    rel = (tr_qv / tr_qv.iloc[0]) / (tr_bm / tr_bm.iloc[0])
    ax.plot(rel, color="darkgreen", lw=1.2)
    ax.axhline(1.0, color="black", lw=0.6)
    ax.set_title("Relative strength (QV / Parent)"); ax.grid(alpha=0.3)

    ax = axes[1, 0]
    ax.plot(drawdown_series(tr_qv), lw=1.0, label="SJFI QV")
    ax.plot(drawdown_series(tr_bm), lw=1.0, color="grey", label="Parent")
    ax.set_title("Drawdown"); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    ax = axes[1, 1]
    to = res_qv.review_turnover
    ax.bar(to.index, to.values, width=45, color="steelblue")
    ax.set_title("Two-way turnover per review (QV index)")
    ax.grid(alpha=0.3)

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT / "backtest_report.png", dpi=140)
    plt.close(fig)

    # ---------------- active factor exposure chart ---------------------
    rows = []
    for cutoff, diag in qv.review_diagnostics.items():
        w = diag["weight"]
        bw = diag["ff_mcap"] / diag["ff_mcap"].sum()
        rows.append({
            "cutoff": cutoff,
            "active_z_value": float(((w - bw) * diag["z_value"]).sum()),
            "active_z_quality": float(((w - bw) * diag["z_quality"]).sum()),
        })
    expo = pd.DataFrame(rows).set_index("cutoff").sort_index()
    fig, ax = plt.subplots(figsize=(9, 4))
    expo.plot(ax=ax, marker="o", ms=3, lw=1.1)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_title("Active factor exposure at each review "
                 "(weight-gap x z-score)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "factor_exposures.png", dpi=140)
    plt.close(fig)

    print(f"\nOutputs written to {OUT}")


if __name__ == "__main__":
    main()
