

"""UTILS/weighted_scoring.py

Interactive scoring utilities.

Goal:
- Define (persona -> 6 attributes) as a single source of truth.
- Provide robust normalization (percentile clipping) so outliers don't dominate.
- Compute a dynamic weighted score (0–100) from user weights (1–5).

This module is intentionally stateless: Dash callbacks pass weights in and get
back a scored dataframe + optional breakdown.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


# -----------------------------
# Persona feature configuration
# -----------------------------
# dir: +1 means higher is better, -1 means lower is better
# label: UI label (nice name)
PERSONA_FEATURES: Dict[str, List[Dict[str, object]]] = {
    "real_estate": [
        {"col": "Real_GDP_per_Capita_USD", "label": "GDP per Capita (USD)", "dir": +1},
        {"col": "Total_Population", "label": "Population", "dir": +1},
        {"col": "Population_Growth_Rate", "label": "Population Growth (%)", "dir": +1},
        {"col": "Net_Migration_Rate", "label": "Net Migration Rate", "dir": +1},
        {"col": "Unemployment_Rate_percent", "label": "Unemployment (%)", "dir": -1},
        {"col": "Public_Debt_percent_of_GDP", "label": "Public Debt (% of GDP)", "dir": -1},
    ],
    "agriculture": [
        {"col": "Ag_Area_km2", "label": "Agricultural Area (km²)", "dir": +1},
        {"col": "Irrigated_Land", "label": "Irrigated Land (km²)", "dir": +1},
        {"col": "Total_Population", "label": "Population", "dir": +1},
        {"col": "Exports_billion_USD", "label": "Exports (B USD)", "dir": +1},
        {"col": "Imports_billion_USD", "label": "Imports (B USD)", "dir": -1},
        {"col": "Ag_Area_per_Capita", "label": "Ag Area per Capita", "dir": +1},
    ],
    "logistics": [
        {"col": "roadways_km", "label": "Roadways (km)", "dir": +1},
        {"col": "railways_km", "label": "Railways (km)", "dir": +1},
        {"col": "airports_paved_runways_count", "label": "Airports (paved runways)", "dir": +1},
        {"col": "Exports_billion_USD", "label": "Exports (B USD)", "dir": +1},
        {"col": "Imports_billion_USD", "label": "Imports (B USD)", "dir": +1},
        {"col": "Coastline", "label": "Coastline (km)", "dir": +1},
    ],
    "telecom": [
        {"col": "Internet_Pen", "label": "Internet Penetration", "dir": +1},
        {"col": "Mobile_Pen", "label": "Mobile Penetration", "dir": +1},
        {"col": "Broadband_Pen", "label": "Broadband Penetration", "dir": +1},
        {"col": "electricity_generating_capacity_kW", "label": "Electricity Capacity (kW)", "dir": +1},
        {"col": "internet_users_total", "label": "Internet Users (Scale)", "dir": +1},
        {"col": "broadband_fixed_subscriptions_total", "label": "Broadband Subs (Scale)", "dir": +1},
    ],
    "fintech": [
        {"col": "Real_GDP_Growth_Rate_percent", "label": "GDP Growth (%)", "dir": +1},
        {"col": "Real_GDP_per_Capita_USD", "label": "GDP per Capita (USD)", "dir": +1},
        {"col": "Internet_Pen", "label": "Internet Penetration", "dir": +1},
        {"col": "Mobile_Pen", "label": "Mobile Penetration", "dir": +1},
        {"col": "Broadband_Pen", "label": "Broadband Penetration", "dir": +1},
        {"col": "broadband_fixed_subscriptions_total", "label": "Broadband Subs (Scale)", "dir": +1},
    ],
}

# Persona-specific microstate penalty tuning.
# (max_penalty, gamma)
PENALTY_PARAMS: Dict[str, Tuple[float, float]] = {
    "real_estate": (35.0, 1.8),
    "agriculture": (30.0, 1.7),
    "logistics": (45.0, 2.2),
    "telecom": (45.0, 2.2),
    "fintech": (40.0, 2.0),
}

def apply_microstate_penalty(
    df: pd.DataFrame,
    score_col: str,
    pop_col: str = "Total_Population",
    max_penalty: float = 25.0,
    gamma: float = 1.6,
):
    """
    Penalize very small countries so they don't dominate rankings.
    Smooth, log-scaled population penalty.
    """

    pop = df[pop_col].fillna(1).astype(float)

    # Log-scale population to avoid extreme skew
    pop_log = np.log10(np.clip(pop, 1, None))

    # Robust normalization (ignores extreme outliers)
    lo = pop_log.quantile(0.05)
    hi = pop_log.quantile(0.95)
    pop_norm = ((pop_log - lo) / (hi - lo)).clip(0, 1)

    # Small population → larger penalty
    penalty = max_penalty * ((1 - pop_norm) ** gamma)

    return (df[score_col] - penalty).clip(0, 100)

# -----------------------------
# Robust normalization
# -----------------------------
def robust_normalize(
    s: pd.Series,
    lower_q: float = 0.05,
    upper_q: float = 0.95,
    fill_value: float = 0.0,
) -> pd.Series:
    """Normalize a numeric series to [0,1] with percentile clipping.

    Steps:
    1) Coerce to numeric.
    2) Compute q_low and q_high.
    3) Clip to [q_low, q_high].
    4) Min-max scale the clipped values to [0,1].

    If the series is constant or empty, returns zeros.
    """
    x = pd.to_numeric(s, errors="coerce").astype(float)
    x = x.replace([np.inf, -np.inf], np.nan).fillna(fill_value)

    if len(x) == 0:
        return pd.Series([], dtype=float)

    q_low = float(x.quantile(lower_q))
    q_high = float(x.quantile(upper_q))

    if np.isclose(q_low, q_high):
        return pd.Series(np.zeros(len(x)), index=x.index, dtype=float)

    x_clip = x.clip(lower=q_low, upper=q_high)
    denom = (q_high - q_low)
    if np.isclose(denom, 0.0):
        return pd.Series(np.zeros(len(x)), index=x.index, dtype=float)

    return (x_clip - q_low) / denom


def apply_direction(norm: pd.Series, direction: int) -> pd.Series:
    """If direction is -1, invert a normalized [0,1] series."""
    return norm if direction >= 0 else (1.0 - norm)


# -----------------------------
# Weighted scoring
# -----------------------------
@dataclass(frozen=True)
class ScoreResult:
    scored_df: pd.DataFrame
    score_col: str
    weights_used: Dict[str, float]


def normalize_weights(raw_weights: Dict[str, float]) -> Dict[str, float]:
    """Convert raw slider weights (e.g., 1–5) into normalized weights summing to 1."""
    cleaned = {k: float(v) for k, v in raw_weights.items() if v is not None}
    total = sum(cleaned.values())
    if total <= 0:
        # fallback: equal weights
        n = max(len(cleaned), 1)
        return {k: 1.0 / n for k in cleaned.keys()}
    return {k: v / total for k, v in cleaned.items()}


def get_persona_feature_defs(persona: str) -> List[Dict[str, object]]:
    if persona not in PERSONA_FEATURES:
        raise KeyError(f"Unknown persona '{persona}'. Known: {list(PERSONA_FEATURES.keys())}")
    return PERSONA_FEATURES[persona]


def default_persona_weights(persona: str, default: int = 3) -> Dict[str, int]:
    """Convenience: returns default slider values (1–5) for all 6 attributes."""
    defs = get_persona_feature_defs(persona)
    return {d["col"]: int(default) for d in defs}


def compute_weighted_score(
    df: pd.DataFrame,
    persona: str,
    raw_weights: Dict[str, float],
    *,
    lower_q: float = 0.05,
    upper_q: float = 0.95,
    output_prefix: str = "dyn",
    return_norm_columns: bool = True,
) -> ScoreResult:
    """Compute a dynamic weighted score (0–100) for a persona.

    Parameters
    - df: preprocessed dataframe (from load_and_process_data)
    - persona: key in PERSONA_FEATURES
    - raw_weights: mapping {column_name: slider_value}, typically 1–5
    - lower_q/upper_q: robust clipping percentiles
    - output_prefix: prefix for generated columns
    - return_norm_columns: if True, keeps per-attribute normalized columns

    Returns
    - ScoreResult(scored_df, score_col, weights_used)

    Notes
    - Missing columns are treated as zeros (but you should ensure preprocessing created them).
    - All normalized attribute columns are in [0,1] after direction.
    """
    defs = get_persona_feature_defs(persona)

    # Ensure we have weights for the six columns
    # (If some are missing, we default them to 3.)
    full_raw = {}
    for d in defs:
        col = str(d["col"])
        full_raw[col] = float(raw_weights.get(col, 3))

    weights = normalize_weights(full_raw)

    out = df.copy()

    # Compute normalized columns
    norm_cols: List[str] = []
    for d in defs:
        col = str(d["col"])
        direction = int(d.get("dir", +1))

        if col not in out.columns:
            out[col] = 0.0

        norm = robust_normalize(out[col], lower_q=lower_q, upper_q=upper_q)
        norm = apply_direction(norm, direction)

        norm_col = f"{output_prefix}_norm__{col}"
        out[norm_col] = norm
        norm_cols.append(norm_col)

    # Weighted sum → 0..1
    score01 = np.zeros(len(out), dtype=float)
    for d in defs:
        col = str(d["col"])
        w = float(weights[col])
        score01 += w * out[f"{output_prefix}_norm__{col}"].to_numpy(dtype=float)

    score_col = f"{output_prefix}_score"

    # Base weighted score (0–100)
    out[score_col] = np.clip(score01 * 100.0, 0.0, 100.0)

    # Keep raw score for debugging / report (optional but useful)
    out[f"{score_col}_raw"] = out[score_col]

    # Apply persona-specific microstate penalty (population-based correction)
    max_p, g = PENALTY_PARAMS.get(persona, (35.0, 1.8))
    out[score_col] = apply_microstate_penalty(
        out,
        score_col=score_col,
        pop_col="Total_Population",
        max_penalty=max_p,
        gamma=g,
    )

    if not return_norm_columns:
        out.drop(columns=norm_cols, inplace=True, errors="ignore")

    return ScoreResult(scored_df=out, score_col=score_col, weights_used=weights)


def build_score_breakdown_for_country(
    scored_df: pd.DataFrame,
    persona: str,
    weights_used: Dict[str, float],
    country_name: str,
    *,
    output_prefix: str = "dyn",
) -> Tuple[List[Dict[str, object]], float]:
    """Create a simple additive breakdown for one country.

    Returns a list of rows:
      {factor, weight, normalized_value, contribution_points}
    and the final score.

    This is handy for waterfall charts.
    """
    defs = get_persona_feature_defs(persona)

    hit = scored_df[scored_df["Country"].astype(str) == str(country_name)]
    if hit.empty:
        return [], 0.0

    row = hit.iloc[0]
    breakdown: List[Dict[str, object]] = []

    total = 0.0
    for d in defs:
        col = str(d["col"])
        label = str(d.get("label", col))
        w = float(weights_used.get(col, 0.0))
        norm_val = float(row.get(f"{output_prefix}_norm__{col}", 0.0))
        contrib = 100.0 * w * norm_val
        total += contrib
        breakdown.append(
            {
                "factor": label,
                "col": col,
                "weight": w,
                "normalized_value": norm_val,
                "contribution": contrib,
            }
        )
    # If we have a penalized score, add the penalty as a final row so the waterfall matches
    penalized = float(row.get(f"{output_prefix}_score", total))
    raw = float(row.get(f"{output_prefix}_score_raw", total))

    if raw != penalized:
        breakdown.append(
            {
                "factor": "Microstate Penalty",
                "col": "Total_Population",
                "weight": 0.0,
                "normalized_value": 0.0,
                "contribution": penalized - raw,  # negative number
            }
        )
    total = penalized

    return breakdown, float(np.clip(total, 0.0, 100.0))