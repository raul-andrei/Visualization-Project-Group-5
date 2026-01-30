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
    """Convert a column to numbers (invalid values become NaN).
    We keep NaN so we can fill missing values in a controlled way later.
    """
    out = pd.to_numeric(s, errors="coerce").astype(float)
    return out.replace([np.inf, -np.inf], np.nan)


def _fill_with_ref_median(x: pd.Series, ref: pd.Series) -> pd.Series:
    """Fill missing values using the median from a reference dataset.
    This is usually more realistic than filling with 0.
    """
    med = float(np.nanmedian(ref.to_numpy(dtype=float)))
    if np.isnan(med):
        med = 0.0
    return x.fillna(med)


# Real Estate baseline algorithm

def compute_real_estate_scores(
    df: pd.DataFrame,
    *,
    fit_df: Optional[pd.DataFrame] = None,
    keep_intermediate: bool = True,
    missing_penalty_enabled: bool = True,
    missing_penalty_max: float = 15.0,
) -> pd.DataFrame:
    """Compute Real Estate Opportunity scores (0-100) for each country.

    What it does:
    1) Cleans the 6 input columns and fills missing values using medians.
    2) Builds 4 main components (wealth, demand, stability, market size) as 0-100 scores.
    3) Applies penalties (microstate + optional missing-data penalty).
    4) Combines everything into the final score: RE_Opp (clipped to 0-100).

    Inputs needed (columns):
    - Real_GDP_per_Capita_USD
    - Total_Population
    - Population_Growth_Rate
    - Net_Migration_Rate
    - Unemployment_Rate_percent
    - Public_Debt_percent_of_GDP

    fit_df:
    - If provided, scaling to 0-100 is based on fit_df (usually the full dataset),
      then applied to df.
    """

    base = df.copy()
    ref = base if fit_df is None else fit_df

    # These are the 6 raw inputs used by the model.
    cols = [
        "Real_GDP_per_Capita_USD",
        "Total_Population",
        "Population_Growth_Rate",
        "Net_Migration_Rate",
        "Unemployment_Rate_percent",
        "Public_Debt_percent_of_GDP",
    ]
   
    # Convert to numeric but keep NaN (so we can track missingness properly).
    for c in cols:
        if c not in base.columns:
            base[c] = np.nan
        if c not in ref.columns:
            ref[c] = np.nan
        base[c] = _as_numeric(base[c])
        ref[c] = _as_numeric(ref[c])

    # Treat extremely low GDP/capita values as missing (often caused by parsing/unit issues).
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

    # Wealth: log(GDP per capita) scaled to 0-100.
    base["Wealth_Log"] = np.log10(base["Real_GDP_per_Capita_USD"].clip(lower=1000))
    wealth_log_ref = np.log10(ref["Real_GDP_per_Capita_USD"].clip(lower=1000))
    base["Wealth_Score"] = scaler.fit(
        wealth_log_ref.to_numpy().reshape(-1, 1)
    ).transform(
        base["Wealth_Log"].to_numpy().reshape(-1, 1)
    ).flatten()

    # Demand: mix of absolute population growth, migration, and growth rate.
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
    
    # One combined demand score (weights reflect how important each part is).
    base["Demand_Score"] = (
        0.5 * base["Abs_Demand_Score"]
        + 0.3 * base["Migration_Score"]
        + 0.2 * base["Rel_Growth_Score"]
    )

    # Stability: lower unemployment + lower debt => higher score.
    risk_factor = (
        0.5 * (base["Unemployment_Rate_percent"].clip(0, 25) / 25.0)
        + 0.5 * (base["Public_Debt_percent_of_GDP"].clip(0, 150) / 150.0)
    )
    base["Stability_Score"] = 100.0 * (1.0 - risk_factor)

    # Market size: log(Population * GDP per capita) scaled to 0–100.
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

    # Microstate penalty: very small countries get a small negative adjustment.
    base["RE_Micro_Penalty"] = np.where(
        base["Total_Population"] < 1_000_000,
        -15,
        np.where(base["Total_Population"] < 5_000_000, -7, 0),
    )

    # Missing-data penalty: if a country is missing many inputs, reduce its score slightly.
    # This is based on the ORIGINAL df values (before we filled missing values).
    if missing_penalty_enabled:
        orig = df.reindex(columns=cols)
        missing_cnt = orig.isna().sum(axis=1).astype(float)
        base["RE_Missing_Count"] = missing_cnt
        base["RE_DataQuality_Penalty"] = -(missing_penalty_max * (missing_cnt / float(len(cols)))).clip(0, missing_penalty_max)
    else:
        base["RE_Missing_Count"] = 0.0
        base["RE_DataQuality_Penalty"] = 0.0

    # Final score: weighted mix of the 4 main components + penalties.
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
    """Filter countries by user ranges and then recompute scores inside that filtered set.

    Behavior:
    1) Applies optional min/max bounds on each of the 6 raw input columns.
    2) Removes countries with too many missing inputs (based on the original values).
    3) Recomputes RE_Opp where the 0-100 scaling is fit on the cohort itself (not the full world).
       This makes the results more "relative" to the countries currently visible.


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

    # Mask starts as "keep everything", then gets narrowed by each bound.
    mask = pd.Series(True, index=cohort.index)

    def _apply_bounds(col: str, lo: Optional[float], hi: Optional[float]) -> None:
        """Update the mask based on optional lower/upper bounds for one column."""
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

    # Filter out countries with too many missing values (using original/unfilled values).
    missing_cnt = cohort.reindex(columns=cols).isna().sum(axis=1)
    cohort = cohort.loc[missing_cnt <= max_missing].copy()

    # If cohort too small, avoid meaningless 0–100 scaling.
    if len(cohort) < 2:
        # Return the cohort (possibly empty) with a placeholder RE_Opp
        if "RE_Opp" not in cohort.columns:
            cohort["RE_Opp"] = np.nan
        return cohort

    # Recompute scores inside the cohort (scaling fit on the cohort itself).
    scored = compute_real_estate_scores(
        cohort,
        fit_df=cohort,
        keep_intermediate=keep_intermediate,
        missing_penalty_enabled=missing_penalty_enabled,
        missing_penalty_max=missing_penalty_max,
    )

    return scored


#Minimal Sanity Check Block
if __name__ == "__main__":
    try:
        # Ensure project root is on sys.path so 'import scoring' works when running this file directly
        import sys
        from pathlib import Path

        project_root = Path(__file__).resolve().parents[1]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from UTILS.data_processing import load_and_process_data

        df = load_and_process_data()

        df_re = compute_real_estate_scores(
            df,
            fit_df=df,            # global baseline for scaling
            keep_intermediate=False
        )

        # Example pre-filter: remove very small-population countries and keep good data quality.
        ranking_df = df_re[
            (df["Total_Population"] >= 500_000) &
            (df_re["RE_Missing_Count"] <= 1)
        ]

        print("\n--- SANITY CHECK (OPTION C): RE_Opp LEADERS / TAIL (0–100) ---")
        print(ranking_df.sort_values("RE_Opp", ascending=False)[["Country", "RE_Opp"]].head(10))
        print(ranking_df.sort_values("RE_Opp", ascending=True)[["Country", "RE_Opp"]].head(10))

        # Example cohort: apply bounds and recompute scores inside that cohort.
        cohort_scored = filter_and_score_real_estate_cohort(
            df,
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