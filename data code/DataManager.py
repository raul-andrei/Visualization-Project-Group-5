import os
import pandas as pd

INPUT_FOLDER = "data"
OUTPUT_FOLDER = "data_curated"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


MISSING_MARKERS = ["", " ", "-", "NA", "N/A", "n/a", "na", "NaN"]


def standardize_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Replace common missing markers with proper NaN."""
    return df.replace(MISSING_MARKERS, pd.NA)


def drop_bad_rows(df: pd.DataFrame, key_col: str = "Country") -> pd.DataFrame:
    """Drop rows without Country and rows where all non-key columns are NaN."""
    if key_col in df.columns:
        before = len(df)
        df = df.dropna(subset=[key_col])
        print(f"  Dropped {before - len(df)} rows without {key_col}")

    non_key_cols = [c for c in df.columns if c != key_col]
    if non_key_cols:
        before = len(df)
        mask_all_empty = df[non_key_cols].isna().all(axis=1)
        df = df[~mask_all_empty]
        print(f"  Dropped {before - len(df)} rows with all values empty")

    return df


def convert_percent_columns(df: pd.DataFrame, percent_cols: list) -> pd.DataFrame:
    """
    For columns like '2.26%' or '37.3%', strip '%' and convert to float.
    If column doesn't exist, ignore it.
    """
    for col in percent_cols:
        if col in df.columns:
            # Work on a copy of the column as string, strip %, then to numeric
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("%", "", regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def convert_numeric_columns(df: pd.DataFrame, numeric_cols: list) -> pd.DataFrame:
    """
    Convert given columns to numeric (float), removing commas first.
    If column doesn't exist, ignore it.
    """
    for col in numeric_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ================== CLEANERS PER FILE ================== #

def clean_communications():
    filename = "communications_data.csv"
    path = os.path.join(INPUT_FOLDER, filename)
    print(f"\n=== Cleaning {path} ===")

    df = pd.read_csv(path)
    df = standardize_missing(df)

    numeric_cols = [
        "telephone_fixed_subscriptions_total",
        "mobile_cellular_subscriptions_total",
        "internet_users_total",
        "broadband_fixed_subscriptions_total",
    ]

    df = convert_numeric_columns(df, numeric_cols)
    df = drop_bad_rows(df, key_col="Country")

    out_path = os.path.join(OUTPUT_FOLDER, "communications_data_clean.csv")
    df.to_csv(out_path, index=False)
    print(f"  ✅ Saved cleaned communications to {out_path}")


def clean_demographics():
    filename = "demographics_data.csv"
    path = os.path.join(INPUT_FOLDER, filename)
    print(f"\n=== Cleaning {path} ===")

    df = pd.read_csv(path)
    df = standardize_missing(df)

    # Percent columns with '%' in values
    percent_cols = [
        "Population_Growth_Rate",
        "Total_Literacy_Rate",
        "Male_Literacy_Rate",
        "Female_Literacy_Rate",
        "Youth_Unemployment_Rate",
    ]

    # Other numeric columns (without % in string)
    numeric_cols = [
        "Total_Population",
        "Birth_Rate",
        "Death_Rate",
        "Net_Migration_Rate",
        "Median_Age",
        "Sex_Ratio",
        "Infant_Mortality_Rate",
        "Total_Fertility_Rate",
    ]

    df = convert_percent_columns(df, percent_cols)
    df = convert_numeric_columns(df, numeric_cols)
    df = drop_bad_rows(df, key_col="Country")

    out_path = os.path.join(OUTPUT_FOLDER, "demographics_data_clean.csv")
    df.to_csv(out_path, index=False)
    print(f"  ✅ Saved cleaned demographics to {out_path}")


def clean_economy():
    filename = "economy_data.csv"
    path = os.path.join(INPUT_FOLDER, filename)
    print(f"\n=== Cleaning {path} ===")

    df = pd.read_csv(path)
    df = standardize_missing(df)

    # All these are numeric (no '%' characters in the sample)
    numeric_cols = [
        "Real_GDP_PPP_billion_USD",
        "GDP_Official_Exchange_Rate_billion_USD",
        "Real_GDP_Growth_Rate_percent",
        "Real_GDP_per_Capita_USD",
        "Unemployment_Rate_percent",
        "Youth_Unemployment_Rate_percent",
        "Budget_billion_USD",
        "Budget_Surplus_billion_USD",
        "Budget_Deficit_percent_of_GDP",
        "Public_Debt_percent_of_GDP",
        "Exports_billion_USD",
        "Imports_billion_USD",
        "Exchange_Rate_per_USD",
        "Population_Below_Poverty_Line_percent",
    ]

    df = convert_numeric_columns(df, numeric_cols)
    df = drop_bad_rows(df, key_col="Country")

    out_path = os.path.join(OUTPUT_FOLDER, "economy_data_clean.csv")
    df.to_csv(out_path, index=False)
    print(f"  ✅ Saved cleaned economy to {out_path}")


def clean_energy():
    filename = "energy_data.csv"
    path = os.path.join(INPUT_FOLDER, filename)
    print(f"\n=== Cleaning {path} ===")

    df = pd.read_csv(path)
    df = standardize_missing(df)

    numeric_cols = [
        "electricity_access_percent",
        "electricity_generating_capacity_kW",
        "coal_metric_tons",
        "petroleum_bbl_per_day",
        "refined_petroleum_products_bbl_per_day",
        "refined_petroleum_exports_bbl_per_day",
        "refined_petroleum_imports_bbl_per_day",
        "natural_gas_cubic_meters",
        "carbon_dioxide_emissions_Mt",
    ]

    df = convert_numeric_columns(df, numeric_cols)
    df = drop_bad_rows(df, key_col="Country")

    out_path = os.path.join(OUTPUT_FOLDER, "energy_data_clean.csv")
    df.to_csv(out_path, index=False)
    print(f"  ✅ Saved cleaned energy to {out_path}")


def clean_geography():
    filename = "geography_data.csv"
    path = os.path.join(INPUT_FOLDER, filename)
    print(f"\n=== Cleaning {path} ===")

    df = pd.read_csv(path)
    df = standardize_missing(df)

    # Percent columns (values like "1.8%")
    percent_cols = [
        "Forest_Land",
        "Other_Land",
        "Agricultural_Land",
        "Arable_Land (%% of Total Agricultural Land)",
        "Permanent_Crops (%% of Total Agricultural Land)",
        "Permanent_Pasture (%% of Total Agricultural Land)",
    ]

    df = convert_percent_columns(df, percent_cols)

    # NOTE: Area/length columns (e.g. "652,230 sq km", "14.2 million sq km")
    # are left as strings for now because they contain units and different scales.
    # If you want, we can later add logic to parse them into pure numeric km²/km.

    df = drop_bad_rows(df, key_col="Country")

    out_path = os.path.join(OUTPUT_FOLDER, "geography_data_clean.csv")
    df.to_csv(out_path, index=False)
    print(f"  ✅ Saved cleaned geography to {out_path}")


def clean_government():
    filename = "government_and_civics_data.csv"
    path = os.path.join(INPUT_FOLDER, filename)
    print(f"\n=== Cleaning {path} ===")

    df = pd.read_csv(path)
    df = standardize_missing(df)

    numeric_cols = ["Suffrage_Age"]

    df = convert_numeric_columns(df, numeric_cols)
    df = drop_bad_rows(df, key_col="Country")

    out_path = os.path.join(OUTPUT_FOLDER, "government_and_civics_clean.csv")
    df.to_csv(out_path, index=False)
    print(f"  ✅ Saved cleaned government & civics to {out_path}")


def clean_transportation():
    filename = "transportation_data.csv"
    path = os.path.join(INPUT_FOLDER, filename)
    print(f"\n=== Cleaning {path} ===")

    df = pd.read_csv(path)
    df = standardize_missing(df)

    numeric_cols = [
        "airports_paved_runways_count",
        "airports_unpaved_runways_count",
        "heliports_count",
        "roadways_km",
        "railways_km",
        "waterways_km",
        "gas_pipelines_km",
        "oil_pipelines_km",
        "refined_products_pipelines_km",
        "water_pipelines_km",
    ]

    df = convert_numeric_columns(df, numeric_cols)
    df = drop_bad_rows(df, key_col="Country")

    out_path = os.path.join(OUTPUT_FOLDER, "transportation_data_clean.csv")
    df.to_csv(out_path, index=False)
    print(f"  ✅ Saved cleaned transportation to {out_path}")


def main():
    clean_communications()
    clean_demographics()
    clean_economy()
    clean_energy()
    clean_geography()
    clean_government()
    clean_transportation()
    print("\n🎯 All datasets cleaned and saved in 'data_curated/'")


if __name__ == "__main__":
    main()
