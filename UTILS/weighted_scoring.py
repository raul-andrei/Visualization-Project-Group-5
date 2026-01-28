"""UTILS/weighted_scoring.py

Real Estate scoring algorithm (baseline).

This module intentionally contains ONLY the Real Estate algorithm.
No personas, no dynamic weighting, no UI helpers.
"""

from typing import Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


def _as_numeric(s: pd.Series) -> pd.Series:
    """Coerce to float, remove inf, keep NaN for proper imputation later."""
    out = pd.to_numeric(s, errors="coerce").astype(float)
    return out.replace([np.inf, -np.inf], np.nan)


def _fill_with_ref_median(x: pd.Series, ref: pd.Series) -> pd.Series:
    """Fill NaN using the median of a reference series."""
    med = float(np.nanmedian(ref.to_numpy(dtype=float)))
    if np.isnan(med):
        med = 0.0
    return x.fillna(med)


# -----------------------------
# Real Estate baseline algorithm
# -----------------------------

def compute_real_estate_scores(
    df: pd.DataFrame,
    *,
    fit_df: Optional[pd.DataFrame] = None,
    keep_intermediate: bool = True,
    missing_penalty_enabled: bool = True,
    missing_penalty_max: float = 15.0,
) -> pd.DataFrame:
    """Compute Real Estate Opportunity scores (0–100).

    Inputs (required columns):
    - Real_GDP_per_Capita_USD
    - Total_Population
    - Population_Growth_Rate
    - Net_Migration_Rate
    - Unemployment_Rate_percent
    - Public_Debt_percent_of_GDP

    Parameters
    - df: dataframe to score
    - fit_df: optional reference dataframe for MinMax fitting
              (use full dataset for global baseline)
    - keep_intermediate: if False, only RE_Opp is kept
    - missing_penalty_enabled: whether to apply missing data penalty
    - missing_penalty_max: max penalty to apply for missing data

    Returns
    - DataFrame with RE_Opp and (optionally) intermediate components
    """

    base = df.copy()
    ref = base if fit_df is None else fit_df

    # --- Numeric cleaning (keep NaN so we can impute sensibly) ---
    cols = [
        "Real_GDP_per_Capita_USD",
        "Total_Population",
        "Population_Growth_Rate",
        "Net_Migration_Rate",
        "Unemployment_Rate_percent",
        "Public_Debt_percent_of_GDP",
    ]

    for c in cols:
        if c not in base.columns:
            base[c] = np.nan
        if c not in ref.columns:
            ref[c] = np.nan
        base[c] = _as_numeric(base[c])
        ref[c] = _as_numeric(ref[c])

    # --- Plausibility guard: GDP per capita ---
    # Values below 1000 USD are implausible for sovereign economies and usually indicate
    # parsing errors (e.g. commas, units) or placeholder values.
    # Treat them as missing so they are median-imputed and penalized via data-quality logic.
    base.loc[base["Real_GDP_per_Capita_USD"] < 1000, "Real_GDP_per_Capita_USD"] = np.nan
    ref.loc[ref["Real_GDP_per_Capita_USD"] < 1000, "Real_GDP_per_Capita_USD"] = np.nan

    # Impute NaN using reference medians (more realistic than defaulting to 0)
    base["Real_GDP_per_Capita_USD"] = _fill_with_ref_median(base["Real_GDP_per_Capita_USD"], ref["Real_GDP_per_Capita_USD"]).clip(lower=1)
    base["Total_Population"] = _fill_with_ref_median(base["Total_Population"], ref["Total_Population"]).clip(lower=1)
    base["Population_Growth_Rate"] = _fill_with_ref_median(base["Population_Growth_Rate"], ref["Population_Growth_Rate"])
    base["Net_Migration_Rate"] = _fill_with_ref_median(base["Net_Migration_Rate"], ref["Net_Migration_Rate"])
    base["Unemployment_Rate_percent"] = _fill_with_ref_median(base["Unemployment_Rate_percent"], ref["Unemployment_Rate_percent"])
    base["Public_Debt_percent_of_GDP"] = _fill_with_ref_median(base["Public_Debt_percent_of_GDP"], ref["Public_Debt_percent_of_GDP"])

    scaler = MinMaxScaler(feature_range=(0, 100))

    # --- Wealth ---
    base["Wealth_Log"] = np.log10(base["Real_GDP_per_Capita_USD"].clip(lower=1000))
    wealth_log_ref = np.log10(ref["Real_GDP_per_Capita_USD"].clip(lower=1000))
    base["Wealth_Score"] = scaler.fit(
        wealth_log_ref.to_numpy().reshape(-1, 1)
    ).transform(
        base["Wealth_Log"].to_numpy().reshape(-1, 1)
    ).flatten()

    # --- Demand ---
    base["Pop_Growth_Abs"] = (
        base["Total_Population"] * base["Population_Growth_Rate"] / 100.0
    ).clip(lower=0)

    pop_growth_abs_ref = (
        ref["Total_Population"] * ref["Population_Growth_Rate"] / 100.0
    ).clip(lower=0)

    base["Abs_Demand_Score"] = scaler.fit(
        pop_growth_abs_ref.to_numpy().reshape(-1, 1)
    ).transform(
        base["Pop_Growth_Abs"].to_numpy().reshape(-1, 1)
    ).flatten()

    base["Rel_Growth_Score"] = (
        base["Population_Growth_Rate"].clip(lower=0, upper=3) / 3.0 * 100.0
    )

    migration_ref = ref["Net_Migration_Rate"]
    base["Migration_Score"] = scaler.fit(
        migration_ref.to_numpy().reshape(-1, 1)
    ).transform(
        base["Net_Migration_Rate"].to_numpy().reshape(-1, 1)
    ).flatten()

    base["Demand_Score"] = (
        0.5 * base["Abs_Demand_Score"]
        + 0.3 * base["Migration_Score"]
        + 0.2 * base["Rel_Growth_Score"]
    )

    # --- Stability ---
    risk_factor = (
        0.5 * (base["Unemployment_Rate_percent"].clip(0, 25) / 25.0)
        + 0.5 * (base["Public_Debt_percent_of_GDP"].clip(0, 150) / 150.0)
    )
    base["Stability_Score"] = 100.0 * (1.0 - risk_factor)

    # --- Market size ---
    base["RE_Market_Raw"] = np.log10(
        (base["Total_Population"] * base["Real_GDP_per_Capita_USD"]).clip(lower=1)
    )

    market_raw_ref = np.log10(
        (ref["Total_Population"] * ref["Real_GDP_per_Capita_USD"]).clip(lower=1)
    )

    base["RE_Market_Score"] = scaler.fit(
        market_raw_ref.to_numpy().reshape(-1, 1)
    ).transform(
        base["RE_Market_Raw"].to_numpy().reshape(-1, 1)
    ).flatten()

    # --- Microstate penalty ---
    base["RE_Micro_Penalty"] = np.where(
        base["Total_Population"] < 1_000_000,
        -15,
        np.where(base["Total_Population"] < 5_000_000, -7, 0),
    )

    # --- Data quality penalty ---
    # Countries with many missing inputs (often replaced by 0 upstream) can look artificially strong/weak.
    # Penalize missingness in the ORIGINAL df columns for transparency.
    if missing_penalty_enabled:
        orig = df.reindex(columns=cols)
        missing_cnt = orig.isna().sum(axis=1).astype(float)
        base["RE_Missing_Count"] = missing_cnt
        base["RE_DataQuality_Penalty"] = -(missing_penalty_max * (missing_cnt / float(len(cols)))).clip(0, missing_penalty_max)
    else:
        base["RE_Missing_Count"] = 0.0
        base["RE_DataQuality_Penalty"] = 0.0

    # --- Final score ---
    re_base = (
        0.30 * base["Wealth_Score"]
        + 0.25 * base["Stability_Score"]
        + 0.25 * base["RE_Market_Score"]
        + 0.20 * base["Demand_Score"]
    )

    base["RE_Opp"] = np.clip(re_base + base["RE_Micro_Penalty"] + base["RE_DataQuality_Penalty"], 0.0, 100.0)

    if not keep_intermediate:
        keep = [
            "Country",
            "RE_Opp",
            "RE_Missing_Count",
            "RE_DataQuality_Penalty",
        ]
        keep = [c for c in keep if c in base.columns]
        base = base[keep]


    return base


def filter_and_score_real_estate_cohort(
    df: pd.DataFrame,
    *,
    # Optional min/max bounds for each of the 6 inputs
    gdp_per_capita_min: Optional[float] = None,
    gdp_per_capita_max: Optional[float] = None,
    population_min: Optional[float] = None,
    population_max: Optional[float] = None,
    pop_growth_min: Optional[float] = None,
    pop_growth_max: Optional[float] = None,
    net_migration_min: Optional[float] = None,
    net_migration_max: Optional[float] = None,
    unemployment_min: Optional[float] = None,
    unemployment_max: Optional[float] = None,
    debt_min: Optional[float] = None,
    debt_max: Optional[float] = None,
    # Data-quality filter
    max_missing: int = 1,
    # Scoring controls
    keep_intermediate: bool = False,
    missing_penalty_enabled: bool = True,
    missing_penalty_max: float = 15.0,
) -> pd.DataFrame:
    """Filter a cohort by any of the 6 RE inputs and recompute RE scores within that cohort (Mode B).

    Behavior:
    1) Applies optional [min,max] bounds on each of the 6 raw input columns.
    2) Applies a missingness filter based on the ORIGINAL (unimputed) values of those 6 columns.
    3) Recomputes RE_Opp where all MinMaxScaler fits are performed on the cohort itself (fit_df=cohort).

    Returns the scored cohort dataframe. If the cohort is too small (<2 rows), returns an empty/NaN-scored frame.
    """

    cols = [
        "Real_GDP_per_Capita_USD",
        "Total_Population",
        "Population_Growth_Rate",
        "Net_Migration_Rate",
        "Unemployment_Rate_percent",
        "Public_Debt_percent_of_GDP",
    ]

    # Start from a copy to avoid side effects
    cohort = df.copy()

    # Ensure numeric for filtering (keep NaN)
    for c in cols:
        if c not in cohort.columns:
            cohort[c] = np.nan
        cohort[c] = _as_numeric(cohort[c])

    # Build bounds mask
    mask = pd.Series(True, index=cohort.index)

    def _apply_bounds(col: str, lo: Optional[float], hi: Optional[float]) -> None:
        nonlocal mask
        if lo is not None:
            mask &= cohort[col] >= lo
        if hi is not None:
            mask &= cohort[col] <= hi

    _apply_bounds("Real_GDP_per_Capita_USD", gdp_per_capita_min, gdp_per_capita_max)
    _apply_bounds("Total_Population", population_min, population_max)
    _apply_bounds("Population_Growth_Rate", pop_growth_min, pop_growth_max)
    _apply_bounds("Net_Migration_Rate", net_migration_min, net_migration_max)
    _apply_bounds("Unemployment_Rate_percent", unemployment_min, unemployment_max)
    _apply_bounds("Public_Debt_percent_of_GDP", debt_min, debt_max)

    cohort = cohort.loc[mask].copy()

    # Missingness filter (based on original/unimputed values)
    missing_cnt = cohort.reindex(columns=cols).isna().sum(axis=1)
    cohort = cohort.loc[missing_cnt <= max_missing].copy()

    # If cohort too small, avoid meaningless MinMax scaling
    if len(cohort) < 2:
        # Return the cohort (possibly empty) with a placeholder RE_Opp
        if "RE_Opp" not in cohort.columns:
            cohort["RE_Opp"] = np.nan
        return cohort

    # Recompute scores within cohort (Mode B)
    scored = compute_real_estate_scores(
        cohort,
        fit_df=cohort,
        keep_intermediate=keep_intermediate,
        missing_penalty_enabled=missing_penalty_enabled,
        missing_penalty_max=missing_penalty_max,
    )

    return scored


# --- Minimal Sanity Check Block ---
if __name__ == "__main__":
    try:
        # Ensure project root is on sys.path so `import scoring` works when running this file directly
        import sys
        from pathlib import Path

        project_root = Path(__file__).resolve().parents[1]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from scoring import load_and_process_data

        df = load_and_process_data()

        df_re = compute_real_estate_scores(
            df,
            fit_df=df,            # global baseline
            keep_intermediate=False
        )

        # --- Option C: Pre-ranking filter (population + data quality) ---
        ranking_df = df_re[
            (df["Total_Population"] >= 500_000) &
            (df_re["RE_Missing_Count"] <= 1)
        ]

        print("\n--- SANITY CHECK (OPTION C): RE_Opp LEADERS / TAIL (0–100) ---")
        print(ranking_df.sort_values("RE_Opp", ascending=False)[["Country", "RE_Opp"]].head(10))
        print(ranking_df.sort_values("RE_Opp", ascending=True)[["Country", "RE_Opp"]].head(10))

        # --- Option B: Filter + recompute cohort scores ---
        cohort_scored = filter_and_score_real_estate_cohort(
            df,
            # Example cohort: user-defined bounds across the 6 inputs
            gdp_per_capita_min= None,
            gdp_per_capita_max=None,
            population_min=18_000_000,
            population_max=18_500_000,
            pop_growth_min= None,
            pop_growth_max=None,
            net_migration_min= None,
            net_migration_max= None,
            unemployment_min= None,
            unemployment_max= None,
            debt_min= None,
            debt_max= None,
            max_missing=1,
            keep_intermediate=False,
        )

        print("\n--- SANITY CHECK (OPTION B): FILTERED + RECOMPUTED COHORT LEADERS / TAIL ---")
        print(cohort_scored.sort_values("RE_Opp", ascending=False)[["Country", "RE_Opp"]].head(10))
        print(cohort_scored.sort_values("RE_Opp", ascending=True)[["Country", "RE_Opp"]].head(10))

    except Exception as e:
        print("Sanity check failed:")
        print(e)