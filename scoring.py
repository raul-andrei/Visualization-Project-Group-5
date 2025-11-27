import pandas as pd
import numpy as np
import os
import re
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA

def load_and_process_data():
    """
    Scoring Engine for 'countries_master_curated.csv'.
    1. Loads the master dataset.
    2. Cleans complex units (e.g., '1.2 million sq km').
    3. Calculates Investment Opportunity & Risk Scores (Scale 0-100).
    """
    
    # ---------------------------------------------------------
    # 1. ROBUST FILE LOADING
    # ---------------------------------------------------------
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    FILE_PATH = os.path.join(SCRIPT_DIR, 'data_curated', 'countries_master_curated.csv')

    


    df = pd.read_csv(FILE_PATH)

    # FILTER: Remove non-country entities
    ignore_list = ['WORLD', 'EUROPEAN UNION', 'ANTARCTICA']
    df = df[~df['Country'].isin(ignore_list)]

   
    # 2. ADVANCED DATA CLEANING
    def clean_numeric(x):
        """
        Parses complex strings: '$12,000', '1.2 million sq km', '5.4%'
        """
        if pd.isna(x): return 0
        if isinstance(x, (int, float)): return x
        
        s = str(x).lower().strip()
        if s in ['-', 'na', 'nan', '']: return 0
        
        multiplier = 1
        if 'million' in s:
            multiplier = 1_000_000
            s = s.replace('million', '')
        if 'billion' in s:
            multiplier = 1_000_000_000
            s = s.replace('billion', '')
            
        s = re.sub(r'[$,%]', '', s)
        s = s.replace('sq km', '').replace('km', '').replace('m', '').strip()
        
        match = re.search(r'-?\d+(\.\d+)?', s)
        if match:
            try:
                return float(match.group()) * multiplier
            except:
                return 0
        return 0

    target_cols = [
        'Area_Total', 'Land_Area', 'Irrigated_Land', 'Agricultural_Land',
        'Real_GDP_per_Capita_USD', 'Real_GDP_Growth_Rate_percent',
        'Public_Debt_percent_of_GDP', 'Unemployment_Rate_percent',
        'Exports_billion_USD', 'Imports_billion_USD',
        'Population_Growth_Rate', 'Net_Migration_Rate', 'Total_Population',
        'roadways_km', 'railways_km', 'airports_paved_runways_count',
        'internet_users_total', 'mobile_cellular_subscriptions_total',
        'electricity_generating_capacity_kW', 'carbon_dioxide_emissions_Mt'
    ]

    for col in target_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric)
        else:
            df[col] = 0 

    # ---------------------------------------------------------
    # 3. MISSING DATA IMPUTATION
    # ---------------------------------------------------------
    df['Total_Population'] = df['Total_Population'].replace(0, 1)
    df['Area_Total'] = df['Area_Total'].replace(0, 1)

    for c in ['Real_GDP_Growth_Rate_percent', 'Unemployment_Rate_percent']:
        if c in df.columns:
            df[c] = df[c].fillna(df[c].median())

    for c in ['railways_km', 'roadways_km', 'internet_users_total']:
        if c in df.columns:
            df[c] = df[c].fillna(0)

    # 4. SCORING ALGORITHMS (0-100 Scale)
    
    # We scale input data to 0-100 first.
    scaler = MinMaxScaler(feature_range=(0, 100))

    #  A. Real Estate
    df['RE_Opp'] = (
        0.4 * scaler.fit_transform(df[['Real_GDP_per_Capita_USD']]) + 
        0.3 * scaler.fit_transform(df[['Population_Growth_Rate']]) +
        0.3 * scaler.fit_transform(df[['Net_Migration_Rate']])
    )

    #  B. Agriculture 
    arable_col = next((c for c in df.columns if 'Arable' in c), 'Agricultural_Land')
    df['Ag_Opp'] = (
        0.4 * scaler.fit_transform(df[[arable_col]]) +
        0.3 * scaler.fit_transform(df[['Irrigated_Land']]) + 
        0.3 * scaler.fit_transform(df[['Agricultural_Land']])
    )

    #  C. Logistics 
    df['Road_Density'] = df['roadways_km'] / df['Area_Total']
    df['Rail_Density'] = df['railways_km'] / df['Area_Total']
    df['Trade_Vol'] = df['Exports_billion_USD'] + df['Imports_billion_USD']

    df['Logistics_Opp'] = (
        0.3 * scaler.fit_transform(df[['Road_Density']]) + 
        0.2 * scaler.fit_transform(df[['Rail_Density']]) +
        0.2 * scaler.fit_transform(df[['airports_paved_runways_count']]) +
        0.3 * scaler.fit_transform(df[['Trade_Vol']])
    )

    # D. Telecom 
    df['Internet_Pen'] = df['internet_users_total'] / df['Total_Population']
    df['Mobile_Pen'] = df['mobile_cellular_subscriptions_total'] / df['Total_Population']
    df['Mobile_Pen'] = df['Mobile_Pen'].clip(upper=1.5)

    df['Telecom_Opp'] = (
        0.5 * scaler.fit_transform(df[['Internet_Pen']]) + 
        0.5 * scaler.fit_transform(df[['Mobile_Pen']])
    )

    #  E. Retail 
    df['Retail_Opp'] = (
        0.4 * scaler.fit_transform(df[['Real_GDP_per_Capita_USD']]) + 
        0.3 * scaler.fit_transform(df[['Total_Population']]) +
        0.3 * scaler.fit_transform(df[['Internet_Pen']])
    )

    #  F. Fintech 
    df['Fintech_Opp'] = (
        0.4 * scaler.fit_transform(df[['Real_GDP_Growth_Rate_percent']]) +
        0.3 * scaler.fit_transform(df[['Mobile_Pen']]) +
        0.3 * scaler.fit_transform(df[['Real_GDP_per_Capita_USD']])
    )

    # --- G. Risk ---
    df['Global_Risk'] = (
        0.5 * scaler.fit_transform(df[['Public_Debt_percent_of_GDP']].fillna(0)) +
        0.5 * scaler.fit_transform(df[['Unemployment_Rate_percent']])
    )

    # ---------------------------------------------------------
    # 5. VISUALIZATION ENGINE (PCA)
    # ---------------------------------------------------------
    pca_cols = ['Real_GDP_per_Capita_USD', 'Real_GDP_Growth_Rate_percent', 'Global_Risk']
    pca_data = df[pca_cols].fillna(0)
    
    # Standardize
    pca_data = (pca_data - pca_data.mean()) / pca_data.std()
    pca_data = pca_data.fillna(0)

    pca = PCA(n_components=2)
    coords = pca.fit_transform(pca_data)
    
    df['PCA_1'] = coords[:, 0]
    df['PCA_2'] = coords[:, 1]

    # Region Proxy
    if 'Government_Type' in df.columns:
        df['Region'] = df['Government_Type'].astype(str).str.split(' ').str[0]
    else:
        df['Region'] = 'Global'

    print(f"Scoring Complete. Processed {len(df)} countries.")
    return df

if __name__ == "__main__":
    df = load_and_process_data()
    if not df.empty:
        # Sanity Check to prove range is 0-100
        print("\n--- SCORES CHECK (Should be 0-100) ---")
        print(df[['Country', 'RE_Opp', 'Telecom_Opp']].head())
        
# Add this to the bottom of scoring.py to print a "Sanity Check" report
if __name__ == "__main__":
    df = load_and_process_data()
    
    print("\n--- SANITY CHECK: WEALTHIEST MARKETS ---")
    # Should show Luxembourg, Singapore, Ireland, etc.
    print(df.sort_values('Real_GDP_per_Capita_USD', ascending=False)[['Country', 'Real_GDP_per_Capita_USD']].head(5))
    
    print("\n--- SANITY CHECK: LARGEST LOGISTICS HUBS ---")
    # Should show USA, China, Germany (High Trade Vol + Infrastructure)
    print(df.sort_values('Logistics_Opp', ascending=False)[['Country', 'Logistics_Opp']].head(5))

if __name__ == "__main__":
    import time
    
    # 1. Start the timer
    start_time = time.time()
    print("Starting data processing...")

    # 2. Run the function
    df = load_and_process_data()

    # 3. Stop the timer
    end_time = time.time()
    duration = end_time - start_time

    # 4. Print results
    print(f"\nDONE! Processed {len(df)} countries in {duration:.4f} seconds.")
    
    if not df.empty:
        print("\n--- SAMPLE SCORES ---")
        print(df[['Country', 'RE_Opp', 'Telecom_Opp', 'Global_Risk']].head())
