# investor_views.py
import pandas as pd
from investor_config import INVESTOR_CONFIG

MASTER_PATH = "data_curated/countries_master_curated.csv"


def load_master() -> pd.DataFrame:
    """Load the master curated dataset."""
    return pd.read_csv(MASTER_PATH)


def get_investor_view(df: pd.DataFrame, investor_key: str):
    """
    Returns:
      df_view: dataframe with Country + all (primary+secondary) cols for this investor
      meta:    dict with label, primary, secondary, filters (only existing columns)
    """
    cfg = INVESTOR_CONFIG[investor_key]

    # All columns this investor might use
    all_cols = sorted(set(cfg["primary"] + cfg["secondary"]))
    cols_existing = [c for c in all_cols if c in df.columns]

    # Slice dataframe
    df_view = df[["Country"] + cols_existing]

    # Clean meta so it only contains existing columns
    primary_existing = [c for c in cfg["primary"] if c in df.columns]
    secondary_existing = [c for c in cfg["secondary"] if c in df.columns]
    filters_existing = [c for c in cfg["filters"] if c in df.columns]

    meta = {
        "label": cfg["label"],
        "primary": primary_existing,
        "secondary": secondary_existing,
        "filters": filters_existing,
    }

    return df_view, meta
