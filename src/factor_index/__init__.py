"""SJFI 500 Quality-Value Factor Index - reference implementation.

A divisor-based equity factor index engine implementing the SJFI 500
Quality-Value Index Ground Rules v1.0: eligibility screening, factor
scoring (tilt methodology), constituent capping, semi-annual reviews,
and corporate-action treatment, with a full daily backtest.
"""

__version__ = "1.0.0"

from .calendar import ReviewCalendar
from .universe import MarketData
from .eligibility import apply_eligibility_screens
from .factors import composite_factor_scores
from .weighting import tilt_weights, apply_capping
from .engine import IndexEngine, IndexResult

__all__ = [
    "ReviewCalendar",
    "MarketData",
    "apply_eligibility_screens",
    "composite_factor_scores",
    "tilt_weights",
    "apply_capping",
    "IndexEngine",
    "IndexResult",
]
