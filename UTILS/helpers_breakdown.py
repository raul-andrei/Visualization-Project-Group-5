# utils/breakdown_helpers.py
import numpy as np
import pandas as pd

def minmax_0_100(series: pd.Series) -> np.ndarray:
    s = series.astype(float).replace([np.inf, -np.inf], 0).fillna(0)
    mn, mx = float(s.min()), float(s.max())
    if mx - mn == 0:
        return np.zeros(len(s))
    return (s - mn) / (mx - mn) * 100.0

def build_breakdown(df: pd.DataFrame, row: pd.Series, persona_key: str):
    def val(col, default=0.0):
        if col in row and pd.notna(row[col]):
            return float(row[col])
        return float(default)

    factors = []
    final_score = None

    if persona_key == "real_estate":
        factors = [
            ("Wealth_Score", val("Wealth_Score"), 0.30),
            ("Stability_Score", val("Stability_Score"), 0.25),
            ("RE_Market_Score", val("RE_Market_Score"), 0.25),
            ("Demand_Score", val("Demand_Score"), 0.20),
            ("RE_Micro_Penalty", val("RE_Micro_Penalty"), 1.00),
        ]
        base = (
            0.30 * val("Wealth_Score") +
            0.25 * val("Stability_Score") +
            0.25 * val("RE_Market_Score") +
            0.20 * val("Demand_Score")
        )
        final_score = float(np.clip(base + val("RE_Micro_Penalty"), 0, 100))

    elif persona_key == "agriculture":
        factors = [
            ("Ag_Output_Score", val("Ag_Output_Score"), 0.30),
            ("Ag_Scale_Score", val("Ag_Scale_Score"), 0.15),
            ("Ag_Land_Size_Score", val("Ag_Land_Size_Score"), 0.25),
            ("Farmland_Share_Score", val("Farmland_Share_Score"), 0.20),
            ("Irrigation_Score", val("Irrigation_Score"), 0.05),
            ("Ag_Tech_Score", val("Ag_Tech_Score"), 0.05),
            ("Ag_Micro_Penalty", val("Ag_Micro_Penalty"), 1.00),
            ("Water_Stress_Penalty", val("Water_Stress_Penalty"), 1.00),
            ("Food_Dependency_Penalty", val("Food_Dependency_Penalty"), 1.00),
        ]
        base = (
            0.30 * val("Ag_Output_Score") +
            0.15 * val("Ag_Scale_Score") +
            0.25 * val("Ag_Land_Size_Score") +
            0.20 * val("Farmland_Share_Score") +
            0.05 * val("Irrigation_Score") +
            0.05 * val("Ag_Tech_Score")
        )
        final_score = float(np.clip(
            base + val("Ag_Micro_Penalty") + val("Water_Stress_Penalty") + val("Food_Dependency_Penalty"),
            0, 100
        ))

    elif persona_key == "logistics":
        trade_eff_score = minmax_0_100(df["Trade_Eff_Area"]) if "Trade_Eff_Area" in df else np.zeros(len(df))
        infra_density_score = minmax_0_100(df["Infra_Density"]) if "Infra_Density" in df else np.zeros(len(df))
        airports_score = minmax_0_100(df["airports_paved_runways_count"]) if "airports_paved_runways_count" in df else np.zeros(len(df))
        port_eff_score = minmax_0_100(df["Port_Eff"]) if "Port_Eff" in df else np.zeros(len(df))
        log_eff_score = minmax_0_100(df["Log_Eff"]) if "Log_Eff" in df else np.zeros(len(df))
        log_market_score = minmax_0_100(df["Log_Market_Raw"]) if "Log_Market_Raw" in df else np.zeros(len(df))

        i = int(row.name)
        factors = [
            ("Trade_Eff_Score", float(trade_eff_score[i]), 0.15),
            ("Infra_Density_Score", float(infra_density_score[i]), 0.20),
            ("Airports_Score", float(airports_score[i]), 0.15),
            ("Log_Market_Score", float(log_market_score[i]), 0.15),
            ("Port_Eff_Score", float(port_eff_score[i]), 0.15),
            ("Log_Eff_Score", float(log_eff_score[i]), 0.15),
            ("Wealth_Score", val("Wealth_Score"), 0.05),
            ("Log_Micro_Penalty", val("Log_Micro_Penalty"), 1.00),
            ("Log_Dev_Adjust", val("Log_Dev_Adjust"), 1.00),
        ]
        base = (
            0.15 * float(trade_eff_score[i]) +
            0.20 * float(infra_density_score[i]) +
            0.15 * float(airports_score[i]) +
            0.15 * float(log_market_score[i]) +
            0.15 * float(port_eff_score[i]) +
            0.15 * float(log_eff_score[i]) +
            0.05 * val("Wealth_Score")
        )
        final_score = float(np.clip(base + val("Log_Micro_Penalty") + val("Log_Dev_Adjust"), 0, 100))

    elif persona_key == "telecom":
        broadband_score = minmax_0_100(df["Broadband_Pen"]) if "Broadband_Pen" in df else np.zeros(len(df))
        internet_pen_score = minmax_0_100(df["Internet_Pen"]) if "Internet_Pen" in df else np.zeros(len(df))

        i = int(row.name)
        factors = [
            ("Infra_Quality_Score", val("Infra_Quality_Score"), 0.45),
            ("Broadband_Pen_Score", float(broadband_score[i]), 0.25),
            ("Internet_Pen_Score", float(internet_pen_score[i]), 0.15),
            ("RE_Market_Score", val("RE_Market_Score"), 0.15),
            ("Telecom_Micro_Penalty", val("Telecom_Micro_Penalty"), 1.00),
        ]
        base = (
            0.45 * val("Infra_Quality_Score") +
            0.25 * float(broadband_score[i]) +
            0.15 * float(internet_pen_score[i]) +
            0.15 * val("RE_Market_Score")
        )
        final_score = float(np.clip(base + val("Telecom_Micro_Penalty"), 0, 100))

    elif persona_key == "fintech":
        factors = [
            ("Fintech_Market_Score", val("Fintech_Market_Score"), 0.35),
            ("Fin_Services_Maturity_Score", val("Fin_Services_Maturity_Score"), 0.20),
            ("Fintech_Digital_Score", val("Fintech_Digital_Score"), 0.15),
            ("Fintech_Infra_Score", val("Fintech_Infra_Score"), 0.10),
            ("Urbanization_Score", val("Urbanization_Score"), 0.10),
            ("Velocity_Score", val("Velocity_Score"), 0.10),
            ("Fintech_Micro_Penalty", val("Fintech_Micro_Penalty"), 1.00),
        ]
        base = (
            0.35 * val("Fintech_Market_Score") +
            0.20 * val("Fin_Services_Maturity_Score") +
            0.15 * val("Fintech_Digital_Score") +
            0.10 * val("Fintech_Infra_Score") +
            0.10 * val("Urbanization_Score") +
            0.10 * val("Velocity_Score")
        )
        final_score = float(np.clip(base + val("Fintech_Micro_Penalty"), 0, 100))

    rows = [{
        "factor": name,
        "value_used": float(score),
        "weight": float(weight),
        "contribution": float(score * weight),
    } for name, score, weight in factors]

    return rows, final_score
