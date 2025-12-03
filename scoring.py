import pandas as pd
import numpy as np
import os
import re
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA

def load_and_process_data():
    """
    Scoring Engine for 'countries_master_curated.csv'.
    1. Loads master dataset.
    2. Cleans text and FIXES SCALE ISSUES.
    3. Calculates Investment Scores (0-100) without double-scaling.
    """
    
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    FILE_PATH = os.path.join(SCRIPT_DIR, 'data_curated', 'countries_master_curated.csv')

    print(f"Loading data from: {FILE_PATH}")
    if not os.path.exists(FILE_PATH):
        print("CRITICAL ERROR: Data file not found.")
        return pd.DataFrame()

    df = pd.read_csv(FILE_PATH)

    # FILTER
    ignore = ['WORLD', 'EUROPEAN UNION', 'ANTARCTICA', 'WALLIS AND FUTUNA']
    df = df[~df['Country'].isin(ignore)]

    # 1. CLEANING
    def clean_numeric(x):
        if pd.isna(x): return 0
        if isinstance(x, (int, float)): return x
        s = str(x).lower().strip()
        if s in ['-', 'na', 'nan', '']: return 0
        
        multiplier = 1
        if 'million' in s: multiplier = 1_000_000
        if 'billion' in s: multiplier = 1_000_000_000
        
        s = re.sub(r'[$,%]', '', s)
        s = s.replace('sq km', '').replace('km', '').replace('m', '').strip()
        
        match = re.search(r'-?\d+(\.\d+)?', s)
        if match:
            try: return float(match.group()) * multiplier
            except: return 0
        return 0

    target_cols = [
        'Area_Total', 'Land_Area', 'Irrigated_Land', 'Agricultural_Land',
        'Real_GDP_per_Capita_USD', 'Real_GDP_Growth_Rate_percent',
        'Public_Debt_percent_of_GDP', 'Unemployment_Rate_percent',
        'Exports_billion_USD', 'Imports_billion_USD',
        'Population_Growth_Rate', 'Net_Migration_Rate', 'Total_Population',
        'roadways_km', 'railways_km', 'airports_paved_runways_count',
        'internet_users_total', 'mobile_cellular_subscriptions_total',
        'electricity_generating_capacity_kW', 'carbon_dioxide_emissions_Mt',
        'broadband_fixed_subscriptions_total', 'Median_Age', 'Coastline'
    ]

    for col in target_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric)
        else:
            df[col] = 0 

    # Normalize Agricultural_Land: if it's stored as a percentage (0-100), convert to area in sq km
    if 'Agricultural_Land' in df.columns and 'Land_Area' in df.columns:
        max_ag_val = df['Agricultural_Land'].max()
        # Heuristic: if max <= 100, treat as percentage of land area
        if max_ag_val <= 100:
            df['Ag_Area_km2'] = (df['Agricultural_Land'].clip(lower=0, upper=100) / 100.0) * df['Land_Area']
        else:
            df['Ag_Area_km2'] = df['Agricultural_Land']
    else:
        df['Ag_Area_km2'] = 0

    # Scale Fix
    def fix_billions(x):
        if x > 10000: return x / 1_000_000_000
        return x

    for c in ['Exports_billion_USD', 'Imports_billion_USD']:
        df[c] = df[c].apply(fix_billions)

    # Imputation
    df['Total_Population'] = df['Total_Population'].replace(0, 1)
    df['Area_Total'] = df['Area_Total'].replace(0, 1)
    
    for c in ['Real_GDP_Growth_Rate_percent', 'Unemployment_Rate_percent']:
        if c in df.columns: df[c] = df[c].fillna(df[c].median())
        
    for c in ['railways_km', 'roadways_km', 'internet_users_total', 'broadband_fixed_subscriptions_total']:
        if c in df.columns: df[c] = df[c].fillna(0)

    # ---------------------------------------------------------
    # 4. SCORING ALGORITHMS
    # ---------------------------------------------------------
    # NOTE: Scaler is set to 0-100. We do NOT need to multiply by 100 again.
    scaler = MinMaxScaler(feature_range=(0, 100))

    # --- 0. COMMON VARIABLES ---
    # Log Wealth
    df['Wealth_Log'] = np.log10(df['Real_GDP_per_Capita_USD'].clip(lower=1000))
    df['Wealth_Score'] = scaler.fit_transform(df[['Wealth_Log']]).flatten()
    
    # Penetration Rates
    df['Internet_Pen'] = (df['internet_users_total'] / df['Total_Population']).fillna(0)
    df['Mobile_Pen'] = (df['mobile_cellular_subscriptions_total'] / df['Total_Population']).fillna(0).clip(upper=1.5)
    
    # Market Scale (Log)
    df['Scale_Raw'] = np.log10(df['internet_users_total'].clip(lower=1000))
    df['Scale_Score'] = scaler.fit_transform(df[['Scale_Raw']]).flatten()

    # --- A. REAL ESTATE ---
    # Demand: combine absolute population growth, relative growth, and migration
    df['Pop_Growth_Abs'] = (df['Total_Population'] * df['Population_Growth_Rate'] / 100).clip(lower=0)
    df['Abs_Demand_Score'] = scaler.fit_transform(df[['Pop_Growth_Abs']]).flatten()

    rel_growth_score = (df['Population_Growth_Rate'].clip(0, 3) / 3 * 100)
    migration_score = scaler.fit_transform(df[['Net_Migration_Rate']].fillna(0)).flatten()

    df['Demand_Score'] = (
        0.5 * df['Abs_Demand_Score'] +
        0.3 * migration_score +
        0.2 * rel_growth_score
    )

    # Stability: unchanged (low debt + low unemployment)
    risk_factor = (
        0.5 * df['Unemployment_Rate_percent'].clip(0, 25) / 25 +
        0.5 * df['Public_Debt_percent_of_GDP'].clip(0, 150) / 150
    )
    df['Stability_Score'] = 100 * (1 - risk_factor)

    # Market size: log of GDP scale (population * GDP per capita)
    df['RE_Market_Raw'] = np.log10((df['Total_Population'] * df['Real_GDP_per_Capita_USD']).clip(lower=1))
    df['RE_Market_Score'] = scaler.fit_transform(df[['RE_Market_Raw']]).flatten()

    # Microstate penalty so tiny jurisdictions don't dominate rankings
    df['RE_Micro_Penalty'] = np.where(
        df['Total_Population'] < 1_000_000, -15,
        np.where(df['Total_Population'] < 5_000_000, -7, 0)
    )

    # Final Real Estate Opportunity score (0-100, clipped)
    re_base = (
        0.30 * df['Wealth_Score'] +
        0.25 * df['Stability_Score'] +
        0.25 * df['RE_Market_Score'] +
        0.20 * df['Demand_Score']
    )
    df['RE_Opp'] = np.clip(re_base + df['RE_Micro_Penalty'], 0, 100)

    # --- B. AGRICULTURE ---
    arable_col = next((c for c in df.columns if 'Arable' in c), 'Agricultural_Land')
    df['Ag_Tech_Score'] = df['Wealth_Score']

    # Farmland share (how much of land area is agricultural)
    df['Farmland_Share'] = (df['Ag_Area_km2'] / df['Land_Area']).replace([np.inf, -np.inf], 0).fillna(0)
    df['Farmland_Share_Score'] = scaler.fit_transform(df[['Farmland_Share']]).flatten()

    # Farmland scale (log of agricultural land area)
    df['Ag_Land_Size_Raw'] = np.log10(df['Ag_Area_km2'].clip(lower=1))
    df['Ag_Land_Size_Score'] = scaler.fit_transform(df[['Ag_Land_Size_Raw']]).flatten()

    # Irrigation intensity (how much of agricultural land is irrigated)
    df['Irrigation_Intensity'] = (df['Irrigated_Land'] / df['Ag_Area_km2'].replace(0, 1)).clip(lower=0, upper=1)
    df['Irrigation_Score'] = scaler.fit_transform(df[['Irrigation_Intensity']]).flatten()

    # Agricultural production scale (land size * irrigated land)
    df['Ag_Scale_Raw'] = np.log10((df['Ag_Area_km2'] * df['Irrigated_Land']).clip(lower=1))
    df['Ag_Scale_Score'] = scaler.fit_transform(df[['Ag_Scale_Raw']]).flatten()

    # Agricultural output proxy (farmland * population)
    df['Ag_Output_Raw'] = np.log10((df['Ag_Area_km2'] * df['Total_Population']).clip(lower=1))
    df['Ag_Output_Score'] = scaler.fit_transform(df[['Ag_Output_Raw']]).flatten()

    # Microstate penalty so tiny jurisdictions don't dominate agricultural rankings
    df['Ag_Micro_Penalty'] = np.where(
        df['Total_Population'] < 1_000_000, -20,
        np.where(df['Total_Population'] < 5_000_000, -8, 0)
    )

    # Base Agriculture Opportunity score (0-100 before penalty)
    ag_base = (
        0.30 * df['Ag_Output_Score'] +
        0.15 * df['Ag_Scale_Score'] +
        0.25 * df['Ag_Land_Size_Score'] +
        0.20 * df['Farmland_Share_Score'] +
        0.05 * df['Irrigation_Score'] +
        0.05 * df['Ag_Tech_Score']
    )

    # Water stress penalty: heavily irrigated systems are more fragile
    df['Water_Stress_Penalty'] = np.where(
        df['Irrigation_Intensity'] > 0.8,
        -10,
        0
    )

    # Food import dependency penalty: net food importers get a small discount
    df['Food_Dependency_Penalty'] = np.where(
        df['Imports_billion_USD'] > df['Exports_billion_USD'],
        -10,
        0
    )

    df['Ag_Opp'] = np.clip(
        ag_base + df['Ag_Micro_Penalty'] + df['Water_Stress_Penalty'] + df['Food_Dependency_Penalty'],
        0,
        100
    )

    # --- C. LOGISTICS ---
    # Road density can explode for tiny jurisdictions, so clip to a reasonable maximum
    df['Road_Density'] = (df['roadways_km'] / df['Area_Total']).replace([np.inf, -np.inf], 0).fillna(0).clip(upper=5)

    # Rail density (km of rail per sq km of land)
    df['Rail_Density'] = (df['railways_km'] / df['Land_Area']).replace([np.inf, -np.inf], 0).fillna(0).clip(upper=0.5)

    trade_vol = df['Exports_billion_USD'] + df['Imports_billion_USD']

    # Trade efficiency: trade volume per sq km (how intensively the territory is used for trade)
    df['Trade_Eff_Area'] = (trade_vol / df['Land_Area']).replace([np.inf, -np.inf], 0).fillna(0)

    # Infrastructure density: combined road + rail density
    df['Infra_Density'] = (df['Road_Density'] + df['Rail_Density'])

    trade_eff_score = scaler.fit_transform(df[['Trade_Eff_Area']]).flatten()
    trade_scale_score = scaler.fit_transform(trade_vol.to_frame()).flatten()
    road_net_score = scaler.fit_transform(df[['roadways_km']]).flatten()
    infra_density_score = scaler.fit_transform(df[['Infra_Density']]).flatten()
    airports_score = scaler.fit_transform(df[['airports_paved_runways_count']]).flatten()

    # Port efficiency: trade volume per km of coastline (0 for landlocked countries)
    if 'Coastline' in df.columns:
        df['Port_Eff'] = (trade_vol / df['Coastline'].replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0)
    else:
        df['Port_Eff'] = 0

    # Overall logistics efficiency: trade efficiency per unit of infrastructure density
    df['Log_Eff'] = (df['Trade_Eff_Area'] / df['Infra_Density'].replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0)

    port_eff_score = scaler.fit_transform(df[['Port_Eff']]).flatten()
    log_eff_score = scaler.fit_transform(df[['Log_Eff']]).flatten()

    # Logistics market size: log of trade volume * population
    df['Log_Market_Raw'] = np.log10((trade_vol * df['Total_Population']).clip(lower=1))
    log_market_score = scaler.fit_transform(df[['Log_Market_Raw']]).flatten()

    quality_score = df['Wealth_Score']

    log_base = (
        0.15 * trade_eff_score +
        0.20 * infra_density_score +
        0.15 * airports_score +
        0.15 * log_market_score +
        0.15 * port_eff_score +
        0.15 * log_eff_score +
        0.05 * quality_score
    )

    # Microstate penalty so tiny jurisdictions with artificially high density don't dominate
    df['Log_Micro_Penalty'] = np.where(
        df['Total_Population'] < 1_000_000, -25,
        np.where(df['Total_Population'] < 5_000_000, -8, 0)
    )

    # Development level adjustment: high-income countries tend to have more mature logistics systems,
    # while very low-income countries face structural constraints.
    df['Log_Dev_Adjust'] = np.where(
        (df['Real_GDP_per_Capita_USD'] >= 20000) & (df['Total_Population'] >= 5_000_000), 7,  # boost only for large, high-income systems
        np.where(df['Real_GDP_per_Capita_USD'] <= 8000, -5, 0)  # slight penalty for low-income, emerging systems
    )

    df['Logistics_Opp'] = np.clip(
        log_base + df['Log_Micro_Penalty'] + df['Log_Dev_Adjust'],
        0,
        100
    )

    # --- D. TELECOM ---
    # Broadband and internet penetration
    df['Broadband_Pen'] = (df['broadband_fixed_subscriptions_total'] / df['Total_Population']).fillna(0)

    broadband_score = scaler.fit_transform(df[['Broadband_Pen']]).flatten()
    internet_pen_score = scaler.fit_transform(df[['Internet_Pen']].fillna(0)).flatten()

    # Infra Quality Proxy: wealth (fiber investment), electricity generation, and mobile penetration
    infra_quality_raw = (
        0.5 * df['Wealth_Score'] +
        0.3 * scaler.fit_transform(df[['electricity_generating_capacity_kW']]).flatten() +
        0.2 * df['Mobile_Pen']
    )
    df['Infra_Quality_Score'] = scaler.fit_transform(infra_quality_raw.to_frame()).flatten()

    # Telecom microstate penalty (small markets can't dominate even if very advanced)
    df['Telecom_Micro_Penalty'] = np.where(
        df['Total_Population'] < 1_000_000, -40,
        np.where(df['Total_Population'] < 5_000_000, -15, 0)
    )

    # Final Telecom Opportunity score: Infra Quality First
    df['Telecom_Opp'] = np.clip(
        0.45 * df['Infra_Quality_Score'] +
        0.25 * broadband_score +
        0.15 * internet_pen_score +
        0.15 * df['RE_Market_Score'] +
        df['Telecom_Micro_Penalty'],
        0,
        100
    )

    # --- E. FINTECH ---
    # Growth signal (unchanged core idea)
    df['Velocity_Score'] = (df['Real_GDP_Growth_Rate_percent'].clip(0, 7) / 7) * 100

    # Digital payments proxy: intersection of mobile and internet usage
    df['Fintech_Digital_Raw'] = (df['Mobile_Pen'] * df['Internet_Pen']).fillna(0)
    df['Fintech_Digital_Score'] = scaler.fit_transform(df[['Fintech_Digital_Raw']]).flatten()

    # Fintech market size: log of population * GDP per capita
    df['Fintech_Market_Raw'] = np.log10((df['Total_Population'] * df['Real_GDP_per_Capita_USD']).clip(lower=1))
    df['Fintech_Market_Score'] = scaler.fit_transform(df[['Fintech_Market_Raw']]).flatten()

    # Ecosystem quality: wealth + connectivity (internet + mobile)
    internet_score_ft = scaler.fit_transform(df[['Internet_Pen']].fillna(0)).flatten()
    mobile_score_ft = scaler.fit_transform(df[['Mobile_Pen']]).flatten()

    fintech_ecosystem_raw = (
        0.5 * df['Wealth_Score'] +
        0.25 * internet_score_ft +
        0.25 * mobile_score_ft
    )
    df['Fintech_Ecosystem_Score'] = scaler.fit_transform(fintech_ecosystem_raw.to_frame()).flatten()

    # Microstate penalty: tiny countries cannot be top global fintech markets
    df['Fintech_Micro_Penalty'] = np.where(
        df['Total_Population'] < 1_000_000, -40,
        np.where(df['Total_Population'] < 5_000_000, -15, 0)
    )

    # --- Fintech: Enhanced Realism Features ---
    # Financial services maturity: wealth + connectivity strength
    df['Fin_Services_Maturity_Raw'] = (
        0.6 * df['Wealth_Score'] +
        0.2 * internet_score_ft +
        0.2 * mobile_score_ft
    )
    df['Fin_Services_Maturity_Score'] = scaler.fit_transform(df[['Fin_Services_Maturity_Raw']]).flatten()

    # Urbanization proxy: internet users relative to population
    df['Urbanization_Proxy'] = (df['internet_users_total'] / df['Total_Population']).clip(lower=0)
    df['Urbanization_Score'] = scaler.fit_transform(df[['Urbanization_Proxy']]).flatten()

    # Fintech Infra Score: electricity generation + broadband quality
    df['Fintech_Infra_Raw'] = (
        0.5 * scaler.fit_transform(df[['electricity_generating_capacity_kW']]).flatten() +
        0.5 * broadband_score
    )
    df['Fintech_Infra_Score'] = scaler.fit_transform(df[['Fintech_Infra_Raw']]).flatten()

    # Final Fintech Opportunity score (enhanced, still fully data-driven)
    df['Fintech_Opp'] = np.clip(
        0.35 * df['Fintech_Market_Score'] +      # population × GDP per capita
        0.20 * df['Fin_Services_Maturity_Score'] +  # financial system sophistication
        0.15 * df['Fintech_Digital_Score'] +     # digital payments momentum
        0.10 * df['Fintech_Infra_Score'] +       # infrastructure readiness
        0.10 * df['Urbanization_Score'] +        # urbanization / digital penetration
        0.10 * df['Velocity_Score'] +            # growth
        df['Fintech_Micro_Penalty'],
        0,
        100
    )
    
    # Fill Retail
    df['Retail_Opp'] = df['Wealth_Score'] * 0.5 + df['Demand_Score'] * 0.5

    # --- GLOBAL RISK ---
    df['Global_Risk'] = (
        0.5 * scaler.fit_transform(df[['Public_Debt_percent_of_GDP']].fillna(0)).flatten() +
        0.5 * scaler.fit_transform(df[['Unemployment_Rate_percent']]).flatten()
    )

    # ---------------------------------------------------------
    # 5. VISUALIZATION
    # ---------------------------------------------------------
    try:
        from neural_engine import get_neural_clusters
        df['PCA_1'], df['PCA_2'] = get_neural_clusters(df)
        print("Neural Clustering Complete.")
    except Exception as e:
        print(f"Neural Engine failed ({e}), using PCA.")
        pca_cols = ['Real_GDP_per_Capita_USD', 'Real_GDP_Growth_Rate_percent', 'Global_Risk']
        pca_data = df[pca_cols].fillna(0)
        pca_data = (pca_data - pca_data.mean()) / pca_data.std()
        pca = PCA(n_components=2)
        coords = pca.fit_transform(pca_data.fillna(0))
        df['PCA_1'] = coords[:, 0]
        df['PCA_2'] = coords[:, 1]

    if 'Government_Type' in df.columns:
        df['Region'] = df['Government_Type'].astype(str).str.split(' ').str[0]
    else:
        df['Region'] = 'Global'

    print(f"Scoring Complete. Processed {len(df)} countries.")
    return df


if __name__ == "__main__":
    df = load_and_process_data()
    print("\n--- SANITY CHECK: RE_Opp LEADERS/TAIL (0-100) ---")
    print(df.sort_values('RE_Opp', ascending=False)[['Country', 'RE_Opp']].head(10))
    print(df.sort_values('RE_Opp', ascending=False)[['Country', 'RE_Opp']].tail(10))
    print("\n--- SANITY CHECK: Ag_Opp LEADERS/TAIL (0-100) ---")
    print(df.sort_values('Ag_Opp', ascending=False)[['Country', 'Ag_Opp']].head(10))
    print(df.sort_values('Ag_Opp', ascending=False)[['Country', 'Ag_Opp']].tail(10))
    print("\n--- SANITY CHECK: Logistics_Opp LEADERS/TAIL (0-100) ---")
    print(df.sort_values('Logistics_Opp', ascending=False)[['Country', 'Logistics_Opp']].head(10))
    print(df.sort_values('Logistics_Opp', ascending=False)[['Country', 'Logistics_Opp']].tail(10))
    print("\n--- SANITY CHECK: Telecom_Opp LEADERS/TAIL (0-100) ---")
    print(df.sort_values('Telecom_Opp', ascending=False)[['Country', 'Telecom_Opp']].head(10))
    print(df.sort_values('Telecom_Opp', ascending=False)[['Country', 'Telecom_Opp']].tail(10))
    print("\n--- SANITY CHECK: Fintech_Opp LEADERS/TAIL (0-100) ---")
    print(df.sort_values('Fintech_Opp', ascending=False)[['Country', 'Fintech_Opp']].head(10))
    print(df.sort_values('Fintech_Opp', ascending=False)[['Country', 'Fintech_Opp']].tail(10))