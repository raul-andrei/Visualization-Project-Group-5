import os
import re
from typing import List

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


# -----------------------------
# Configuration
# -----------------------------
IGNORE_ENTITIES = ["WORLD", "EUROPEAN UNION", "ANTARCTICA", "WALLIS AND FUTUNA"]

# Columns we want numeric-cleaned if present (otherwise create them as 0)
TARGET_COLS: List[str] = [
    "Area_Total",
    "Land_Area",
    "Irrigated_Land",
    "Agricultural_Land",
    "Real_GDP_per_Capita_USD",
    "Real_GDP_Growth_Rate_percent",
    "Public_Debt_percent_of_GDP",
    "Unemployment_Rate_percent",
    "Exports_billion_USD",
    "Imports_billion_USD",
    "Population_Growth_Rate",
    "Net_Migration_Rate",
    "Total_Population",
    "roadways_km",
    "railways_km",
    "airports_paved_runways_count",
    "internet_users_total",
    "mobile_cellular_subscriptions_total",
    "electricity_generating_capacity_kW",
    "carbon_dioxide_emissions_Mt",
    "broadband_fixed_subscriptions_total",
    "Median_Age",
    "Coastline",
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


def impute_and_guard_denominators(df: pd.DataFrame) -> pd.DataFrame:
    """Avoid division-by-zero and fill a few key missing values consistently."""
    # denominators used for rates/densities
    if "Total_Population" in df.columns:
        df["Total_Population"] = df["Total_Population"].replace(0, 1)
    if "Area_Total" in df.columns:
        df["Area_Total"] = df["Area_Total"].replace(0, 1)

    for c in ["Real_GDP_Growth_Rate_percent", "Unemployment_Rate_percent"]:
        if c in df.columns:
            df[c] = df[c].fillna(df[c].median())

    for c in ["railways_km", "roadways_km", "internet_users_total", "broadband_fixed_subscriptions_total"]:
        if c in df.columns:
            df[c] = df[c].fillna(0)

    return df


def derive_ag_area(df: pd.DataFrame) -> pd.DataFrame:
    """Create Ag_Area_km2 from Agricultural_Land + Land_Area when Agricultural_Land is a percent."""
    if "Agricultural_Land" in df.columns and "Land_Area" in df.columns:
        max_ag_val = df["Agricultural_Land"].max()
        # If max <= 100, treat as percent
        if max_ag_val <= 100:
            df["Ag_Area_km2"] = (
                df["Agricultural_Land"].clip(lower=0, upper=100) / 100.0
            ) * df["Land_Area"]
        else:
            df["Ag_Area_km2"] = df["Agricultural_Land"]
    else:
        df["Ag_Area_km2"] = 0.0
    return df


# -----------------------------
# Feature engineering
# -----------------------------



def derive_common_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derived variables used across personas and later for interactive scoring."""
    scaler_0_100 = MinMaxScaler(feature_range=(0, 100))

    # Wealth score (log GDP/capita)
    df["Wealth_Log"] = np.log10(df["Real_GDP_per_Capita_USD"].clip(lower=1000))
    df["Wealth_Score"] = scaler_0_100.fit_transform(df[["Wealth_Log"]]).flatten()

    # Penetration rates
    df["Internet_Pen"] = (
        df["internet_users_total"] / df["Total_Population"]
    ).replace([np.inf, -np.inf], 0).fillna(0)
    df["Mobile_Pen"] = (
        df["mobile_cellular_subscriptions_total"] / df["Total_Population"]
    ).replace([np.inf, -np.inf], 0).fillna(0).clip(upper=1.5)
    df["Broadband_Pen"] = (
        df["broadband_fixed_subscriptions_total"] / df["Total_Population"]
    ).replace([np.inf, -np.inf], 0).fillna(0)

    # Agriculture per-capita capacity (avoid scale bias from large populations)
    # Higher is better: more agricultural area available per person
    df["Ag_Area_per_Capita"] = (
        df["Ag_Area_km2"] / df["Total_Population"].replace(0, 1)
    ).replace([np.inf, -np.inf], 0).fillna(0)

    # Optional: market scale score (log internet users)
    df["Scale_Raw"] = np.log10(df["internet_users_total"].clip(lower=1000))
    df["Scale_Score"] = scaler_0_100.fit_transform(df[["Scale_Raw"]]).flatten()

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
    df = derive_ag_area(df)
    df = apply_unit_fixes(df)
    df = impute_and_guard_denominators(df)

    # Common derived features (kept)
    df = derive_common_features(df)

    print(f"Preprocessing complete. Processed {len(df)} countries.")
    return df


if __name__ == "__main__":
    df = load_and_process_data()
    print(df[["Country", "Ag_Area_km2", "Ag_Area_per_Capita", "Internet_Pen", "Mobile_Pen", "Broadband_Pen", "Wealth_Score"]].head())