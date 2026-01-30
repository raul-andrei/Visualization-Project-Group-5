"""UTILS/helpers_breakdown.py

Breakdown helpers for explaining an already-computed score.

This module intentionally supports ONLY the Real Estate persona.
It does NOT compute scores from raw inputs; it only decomposes the
columns that were produced by compute_real_estate_scores.
"""

import numpy as np
import pandas as pd


def build_breakdown(df: pd.DataFrame, row: pd.Series, persona_key: str):
    """Build a clear breakdown of how the final score was formed (for the UI).
    
     This function assumes the row already contains the Real Estate score columns
    (like Wealth_Score, Stability_Score, etc.). It does not re-calculate them from scratch.
    
    Parameters
    - df: full dataframe (unused for real_estate, kept for call-site compatibility)
    - row: a single row (Series) that already contains computed RE columns
    - persona_key: must be "real_estate"

    Returns
    - rows: list of dicts with factor, value_used, weight, contribution
    - final_score: reconstructed RE score (0-100)
    """

    if persona_key != "real_estate":
        raise ValueError("helpers_breakdown currently supports only persona_key='real_estate'.")

    def val(col: str, default: float = 0.0) -> float:
        if col in row and pd.notna(row[col]):
            return float(row[col])
        return float(default)

    # Factors used by the Real Estate score
    factors = [
        ("Wealth_Score", val("Wealth_Score"), 0.30),
        ("Stability_Score", val("Stability_Score"), 0.25),
        ("RE_Market_Score", val("RE_Market_Score"), 0.25),
        ("Demand_Score", val("Demand_Score"), 0.20),
        ("RE_Micro_Penalty", val("RE_Micro_Penalty"), 1.00),
    ]

    # Optional: data-quality penalty (added in weighted_scoring.py)
    if "RE_DataQuality_Penalty" in row:
        factors.append(("RE_DataQuality_Penalty", val("RE_DataQuality_Penalty"), 1.00))
    
    # Main weighted part of the score (0–100).
    base = (
        0.30 * val("Wealth_Score")
        + 0.25 * val("Stability_Score")
        + 0.25 * val("RE_Market_Score")
        + 0.20 * val("Demand_Score")
    )
    
    # Add penalties/adjustments and keep the final score inside 0-100.
    final_score = float(
        np.clip(
            base + val("RE_Micro_Penalty") + val("RE_DataQuality_Penalty"),
            0.0,
            100.0,
        )
    )

    # Turn factors into a list of rows that the UI can display.
    rows = [
        {
            "factor": name,
            "value_used": float(score),
            "weight": float(weight),
            "contribution": float(score * weight),
        }
        for name, score, weight in factors
    ]

    return rows, final_score

