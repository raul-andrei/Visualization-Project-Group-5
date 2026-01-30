import os
from functools import reduce
import pandas as pd

# Folder where the cleaned category CSVs are stored.
INPUT_FOLDER = "data_curated"  

# Final merged dataset (used by the app).
MASTER_OUTPUT = os.path.join(INPUT_FOLDER, "countries_master_curated.csv")


def load_clean_csv(filename: str) -> pd.DataFrame:
    """Load one cleaned CSV file from the curated data folder."""
    path = os.path.join(INPUT_FOLDER, filename)
    print(f"Loading {path}")
    return pd.read_csv(path)


def drop_globally_incomplete_rows(df: pd.DataFrame,
                                  key_col: str = "Country",
                                  min_non_missing_ratio: float = 0.3) -> pd.DataFrame:
    """
    Drop rows that have too many missing values overall.
    Example: ratio 0.3 = keep rows where at least 30% of columns are non-missing.
    """
    # exclude key column from this ratio
    cols = [c for c in df.columns if c != key_col]
    non_missing_counts = df[cols].notna().sum(axis=1)
    ratio = non_missing_counts / len(cols)

    before = len(df)
    df = df[ratio >= min_non_missing_ratio]
    print(f"Dropped {before - len(df)} rows with < {min_non_missing_ratio:.0%} non-missing data")
    return df


def main():
    """Merge all cleaned category datasets into one master countries file."""

    # 1) Load all cleaned files
    dfs = [
        load_clean_csv("communications_data_clean.csv"),
        load_clean_csv("demographics_data_clean.csv"),
        load_clean_csv("economy_data_clean.csv"),
        load_clean_csv("energy_data_clean.csv"),
        load_clean_csv("geography_data_clean.csv"),
        load_clean_csv("government_and_civics_clean.csv"),
        load_clean_csv("transportation_data_clean.csv"),
    ]

    # 2) Outer-merge them on Country
    print("\nMerging on Country (outer join)...")
    master = reduce(
        lambda left, right: pd.merge(left, right, on="Country", how="outer"),
        dfs
    )
    print("Master shape before global filtering:", master.shape)

    # 3) Remove obvious non-countries (oceans etc.) if still there
    NON_COUNTRIES = ["ANTARCTICA", "ARCTIC OCEAN", "ATLANTIC OCEAN",
                     "PACIFIC OCEAN", "INDIAN OCEAN"]
    before = len(master)
    master = master[~master["Country"].isin(NON_COUNTRIES)]
    print(f"Dropped {before - len(master)} non-country rows")

    # 4) Drop globally incomplete countries (too many NaNs across all fields)
    master = drop_globally_incomplete_rows(
        master,
        key_col="Country",
        min_non_missing_ratio=0.3  # tweak this if you want stricter/looser
    )

    print("Final master shape:", master.shape)

    # 5) Save master CSV
    master.to_csv(MASTER_OUTPUT, index=False)
    print(f"\n✅ Saved master dataset to: {MASTER_OUTPUT}")


if __name__ == "__main__":
    main()
