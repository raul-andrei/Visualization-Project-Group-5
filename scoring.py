import os
import re
from typing import List, Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


# -----------------------------
# Configuration
# -----------------------------
IGNORE_ENTITIES = ["WORLD", "EUROPEAN UNION", "ANTARCTICA"]

# Columns we want numeric-cleaned if present (otherwise create them as 0)
# (For now: only the 6 Real Estate inputs)
TARGET_COLS: List[str] = [
    "Real_GDP_per_Capita_USD",
    "Total_Population",
    "Population_Growth_Rate",
    "Net_Migration_Rate",
    "Unemployment_Rate_percent",
    "Public_Debt_percent_of_GDP",
]


# -----------------------------
# Helpers: parsing + cleaning
# -----------------------------
def clean_numeric(x) -> float:
    """Parse messy numeric strings such as '$1.2 billion', '10,000 sq km', '-', 'na'."""
    if pd.isna(x):
        return 0.0
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)

    s = str(x).lower().strip()
    if s in ["-", "na", "nan", ""]:
        return 0.0

    multiplier = 1.0
    if "million" in s:
        multiplier = 1_000_000.0
    if "billion" in s:
        multiplier = 1_000_000_000.0

    # remove common symbols/units
    s = re.sub(r"[$,%]", "", s)
    s = s.replace("sq km", "").replace("km", "").replace("m", "").strip()

    match = re.search(r"-?\d+(\.\d+)?", s)
    if not match:
        return 0.0

    try:
        return float(match.group()) * multiplier
    except Exception:
        return 0.0


def fix_billions(x: float) -> float:
    """If exports/imports were accidentally parsed as absolute USD, convert to billions (heuristic)."""
    # If value looks like a big absolute number, turn into billions.
    if x > 10000:
        return x / 1_000_000_000.0
    return x


def filter_non_countries(df: pd.DataFrame) -> pd.DataFrame:
    if "Country" not in df.columns:
        return df
    return df[~df["Country"].isin(IGNORE_ENTITIES)].copy()


def ensure_numeric_columns(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """Ensure columns exist and are numeric-cleaned."""
    for col in cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric)
        else:
            df[col] = 0.0
    return df


def apply_unit_fixes(df: pd.DataFrame) -> pd.DataFrame:
    for c in ["Exports_billion_USD", "Imports_billion_USD"]:
        if c in df.columns:
            df[c] = df[c].apply(fix_billions)
    return df

# -----------------------------
# Feature engineering
# -----------------------------

# -----------------------------
# Real Estate: feature functions (no final scoring)
# -----------------------------

def _scaler_0_100() -> MinMaxScaler:
    return MinMaxScaler(feature_range=(0, 100))


def compute_wealth_score(
    df: pd.DataFrame,
    fit_df: Optional[pd.DataFrame] = None,
) -> pd.Series:
    """Wealth proxy for RE: min-max scaled log10(GDP/capita).

    - Uses only Real_GDP_per_Capita_USD.
    - If fit_df is provided, the scaler is fit on fit_df (global baseline) but applied to df.
    """
    if fit_df is None:
        fit_df = df
    scaler = _scaler_0_100()

    wealth_log_fit = np.log10(fit_df["Real_GDP_per_Capita_USD"].clip(lower=1000))
    scaler.fit(wealth_log_fit.to_frame())

    wealth_log = np.log10(df["Real_GDP_per_Capita_USD"].clip(lower=1000))
    return pd.Series(scaler.transform(wealth_log.to_frame()).flatten(), index=df.index, name="Wealth_Score")


def compute_re_market_score(
    df: pd.DataFrame,
    fit_df: Optional[pd.DataFrame] = None,
) -> tuple[pd.Series, pd.Series]:
    """Market size proxy for RE.

    Returns:
      - RE_Market_Raw: log10(Population * GDP/capita)
      - RE_Market_Score: min-max scaled RE_Market_Raw

    Uses only Total_Population and Real_GDP_per_Capita_USD.
    """
    if fit_df is None:
        fit_df = df
    scaler = _scaler_0_100()

    raw_fit = np.log10((fit_df["Total_Population"] * fit_df["Real_GDP_per_Capita_USD"]).clip(lower=1))
    scaler.fit(raw_fit.to_frame())

    raw = np.log10((df["Total_Population"] * df["Real_GDP_per_Capita_USD"]).clip(lower=1))
    score = scaler.transform(raw.to_frame()).flatten()

    return (
        pd.Series(raw.values, index=df.index, name="RE_Market_Raw"),
        pd.Series(score, index=df.index, name="RE_Market_Score"),
    )


def compute_re_demand_features(
    df: pd.DataFrame,
    fit_df: Optional[pd.DataFrame] = None,
    rel_growth_clip_max: float = 3.0,
) -> dict[str, pd.Series]:
    """Demand-side RE features.

    Creates:
      - Pop_Growth_Abs: (Population * PopGrowthRate / 100), clipped at >=0
      - Abs_Demand_Score: min-max scaled Pop_Growth_Abs
      - Rel_Growth_Score: Pop growth rate mapped to 0-100 by clipping to [0, rel_growth_clip_max]
      - Migration_Score: min-max scaled Net_Migration_Rate

    Uses only Total_Population, Population_Growth_Rate, Net_Migration_Rate.

    Note: The final Demand_Score aggregation is intentionally NOT done here.
    """
    if fit_df is None:
        fit_df = df

    # Absolute population growth
    pop_growth_abs_fit = (fit_df["Total_Population"] * fit_df["Population_Growth_Rate"] / 100.0).clip(lower=0)
    pop_growth_abs = (df["Total_Population"] * df["Population_Growth_Rate"] / 100.0).clip(lower=0)

    abs_scaler = _scaler_0_100()
    abs_scaler.fit(pop_growth_abs_fit.to_frame())
    abs_score = abs_scaler.transform(pop_growth_abs.to_frame()).flatten()

    # Relative growth mapped directly to 0..100
    rel_growth = (df["Population_Growth_Rate"].clip(lower=0, upper=rel_growth_clip_max) / rel_growth_clip_max) * 100.0

    # Migration score (scaled)
    mig_scaler = _scaler_0_100()
    mig_fit = fit_df[["Net_Migration_Rate"]].fillna(0)
    mig_scaler.fit(mig_fit)
    mig_score = mig_scaler.transform(df[["Net_Migration_Rate"]].fillna(0)).flatten()

    return {
        "Pop_Growth_Abs": pd.Series(pop_growth_abs.values, index=df.index, name="Pop_Growth_Abs"),
        "Abs_Demand_Score": pd.Series(abs_score, index=df.index, name="Abs_Demand_Score"),
        "Rel_Growth_Score": pd.Series(rel_growth.values, index=df.index, name="Rel_Growth_Score"),
        "Migration_Score": pd.Series(mig_score, index=df.index, name="Migration_Score"),
    }


def compute_stability_score(
    df: pd.DataFrame,
    unemployment_clip_max: float = 25.0,
    debt_clip_max: float = 150.0,
) -> pd.Series:
    """Stability proxy for RE (higher is better).

    Uses only Unemployment_Rate_percent and Public_Debt_percent_of_GDP.
    The score is computed deterministically (no min-max scaling).
    """
    risk = (
        0.5 * (df["Unemployment_Rate_percent"].clip(lower=0, upper=unemployment_clip_max) / unemployment_clip_max)
        + 0.5 * (df["Public_Debt_percent_of_GDP"].clip(lower=0, upper=debt_clip_max) / debt_clip_max)
    )
    stability = 100.0 * (1.0 - risk)
    return pd.Series(stability.values, index=df.index, name="Stability_Score")



def derive_common_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derived variables used across personas and later for interactive scoring."""
    scaler_0_100 = MinMaxScaler(feature_range=(0, 100))

    # Wealth score (log GDP/capita)
    df["Wealth_Log"] = np.log10(df["Real_GDP_per_Capita_USD"].clip(lower=1000))
    df["Wealth_Score"] = scaler_0_100.fit_transform(df[["Wealth_Log"]]).flatten()

    return df



# -----------------------------
# Main entrypoint
# -----------------------------
def load_and_process_data() -> pd.DataFrame:
    """Load + clean + derive common features. Persona scoring will be computed interactively in Dash."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "data_curated", "countries_master_curated.csv")

    print(f"Loading data from: {file_path}")
    if not os.path.exists(file_path):
        print("CRITICAL ERROR: Data file not found.")
        return pd.DataFrame()

    df = pd.read_csv(file_path)

    # Cleaning pipeline
    df = filter_non_countries(df)
    df = ensure_numeric_columns(df, TARGET_COLS)
    df = apply_unit_fixes(df)


    # Common derived features (kept)
    df = derive_common_features(df)

    print(f"Preprocessing complete. Processed {len(df)} countries.")
    return df


if __name__ == "__main__":
    df = load_and_process_data()
    cols = [
        "Country",
        "Real_GDP_per_Capita_USD",
        "Total_Population",
        "Population_Growth_Rate",
        "Net_Migration_Rate",
        "Unemployment_Rate_percent",
        "Public_Debt_percent_of_GDP",
        "Wealth_Score",
    ]
    cols = [c for c in cols if c in df.columns]
    print(df[cols].head())