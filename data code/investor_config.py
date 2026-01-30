# investor_config.py

"""Configuration for each investor type (persona) in the project.

For every investor key (like "real_estate" or "telecom"), we define:
- label: how it appears in the UI
- primary: the most important columns to show first
- secondary: extra columns to show for more detail
- filters: columns that are good candidates for filtering (sliders, ranges, etc.)
"""

INVESTOR_CONFIG = {
    "real_estate": {
        "label": "Real Estate & Urban Development",
        # Core indicators for real estate decisions (market size, growth, income, connectivity).
        "primary": [
            "Total_Population",
            "Population_Growth_Rate",
            "Median_Age",
            "Real_GDP_per_Capita_USD",
            "Real_GDP_Growth_Rate_percent",
            "Unemployment_Rate_percent",
            "internet_users_total",
            "broadband_fixed_subscriptions_total",
            "mobile_cellular_subscriptions_total",
        ],
        # Extra context that can affect real estate potential and infrastructure.
        "secondary": [
            "Net_Migration_Rate",
            "Youth_Unemployment_Rate",
            "Population_Below_Poverty_Line_percent",
            "Public_Debt_percent_of_GDP",
            "Area_Total",
            "Land_Area",
            "Agricultural_Land",
            "Irrigated_Land",
            "roadways_km",
            "railways_km",
            "airports_paved_runways_count",
        ],
        # Columns we expect to be useful for filters in the UI.
        "filters": [
            "Real_GDP_per_Capita_USD",
            "Real_GDP_Growth_Rate_percent",
            "Population_Growth_Rate",
            "Youth_Unemployment_Rate",
        ],
    },

    "agriculture": {
        "label": "Agriculture & Agri-business",
        # Indicators related to land, water, productivity conditions, and demand.
        "primary": [
            "Total_Population",
            "Population_Growth_Rate",
            "Real_GDP_Growth_Rate_percent",
            "Agricultural_Land",
            "Arable_Land (%% of Total Agricultural Land)",
            "Irrigated_Land",
            "electricity_access_percent",
        ],
        # Extra context: trade, infrastructure, and land composition.
        "secondary": [
            "Permanent_Crops (%% of Total Agricultural Land)",
            "Permanent_Pasture (%% of Total Agricultural Land)",
            "Area_Total",
            "Land_Area",
            "Water_Area",
            "Exports_billion_USD",
            "Imports_billion_USD",
            "electricity_generating_capacity_kW",
            "roadways_km",
            "railways_km",
            "waterways_km",
        ],
        # Columns that make sense to filter when searching for farming opportunities.
        "filters": [
            "Agricultural_Land",
            "Arable_Land (%% of Total Agricultural Land)",
            "Irrigated_Land",
        ],
    },

    "transport": {
        "label": "Transportation & Logistics",
        # Indicators for market size, trade flows, and transport infrastructure.
        "primary": [
            "Total_Population",
            "Real_GDP_PPP_billion_USD",
            "Real_GDP_Growth_Rate_percent",
            "Exports_billion_USD",
            "Imports_billion_USD",
            "airports_paved_runways_count",
            "roadways_km",
            "railways_km",
            "waterways_km",
        ],
        # Extra context: geography constraints and energy pipelines.
        "secondary": [
            "Population_Growth_Rate",
            "Coastline",
            "Land_Boundaries",
            "Area_Total",
            "airports_unpaved_runways_count",
            "heliports_count",
            "gas_pipelines_km",
            "oil_pipelines_km",
            "refined_products_pipelines_km",
            "petroleum_bbl_per_day",
            "refined_petroleum_products_bbl_per_day",
            "refined_petroleum_exports_bbl_per_day",
            "refined_petroleum_imports_bbl_per_day",
        ],
        # Filters useful for a logistics-focused view.
        "filters": [
            "Real_GDP_PPP_billion_USD",
            "Exports_billion_USD",
            "Imports_billion_USD",
        ],
    },

    "telecom": {
        "label": "Telecom & Digital Infrastructure",
        # Indicators for demand (population/age) and usage (mobile/internet/broadband).
        "primary": [
            "Total_Population",
            "Median_Age",
            "Real_GDP_per_Capita_USD",
            "mobile_cellular_subscriptions_total",
            "internet_users_total",
            "broadband_fixed_subscriptions_total",
        ],
        # Extra context: education, unemployment, energy access, and country code info.
        "secondary": [
            "telephone_fixed_subscriptions_total",
            "Population_Growth_Rate",
            "Total_Literacy_Rate",
            "Male_Literacy_Rate",
            "Female_Literacy_Rate",
            "Youth_Unemployment_Rate",
            "Real_GDP_Growth_Rate_percent",
            "Unemployment_Rate_percent",
            "Public_Debt_percent_of_GDP",
            "electricity_access_percent",
            "electricity_generating_capacity_kW",
            "internet_country_code",
        ],
        # Filters that match the core telecom adoption metrics.
        "filters": [
            "mobile_cellular_subscriptions_total",
            "internet_users_total",
            "broadband_fixed_subscriptions_total",
        ],
    },

    "retail": {
        "label": "Retail & E-commerce",
        # Indicators for consumer market size, income, growth, and online reach.
        "primary": [
            "Total_Population",
            "Population_Growth_Rate",
            "Median_Age",
            "Real_GDP_per_Capita_USD",
            "Real_GDP_Growth_Rate_percent",
            "mobile_cellular_subscriptions_total",
            "internet_users_total",
        ],
        # Extra context: purchasing constraints and infrastructure.
        "secondary": [
            "Youth_Unemployment_Rate",
            "Total_Literacy_Rate",
            "Unemployment_Rate_percent",
            "Population_Below_Poverty_Line_percent",
            "Exchange_Rate_per_USD",
            "broadband_fixed_subscriptions_total",
            "electricity_access_percent",
            "roadways_km",
        ],
        # Filters that help find growing consumer markets.
        "filters": [
            "Real_GDP_per_Capita_USD",
            "Population_Growth_Rate",
            "internet_users_total",
        ],
    },

    "fintech": {
        "label": "Financial Services & Fintech",
        # Indicators for customer base, growth, income, and digital access.
        "primary": [
            "Total_Population",
            "Median_Age",
            "Real_GDP_per_Capita_USD",
            "Real_GDP_Growth_Rate_percent",
            "mobile_cellular_subscriptions_total",
            "internet_users_total",
        ],
        # Extra context: education, unemployment, public finance, and infrastructure.
        "secondary": [
            "Youth_Unemployment_Rate",
            "Total_Literacy_Rate",
            "Male_Literacy_Rate",
            "Female_Literacy_Rate",
            "Unemployment_Rate_percent",
            "Youth_Unemployment_Rate_percent",
            "Population_Below_Poverty_Line_percent",
            "Public_Debt_percent_of_GDP",
            "Exchange_Rate_per_USD",
            "broadband_fixed_subscriptions_total",
            "electricity_access_percent",
        ],
        # Filters tied to target audience size and digital adoption.
        "filters": [
            "Real_GDP_per_Capita_USD",
            "Youth_Unemployment_Rate",
            "mobile_cellular_subscriptions_total",
            "internet_users_total",
        ],
    },
}
