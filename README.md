# Visualization-Project-Group-5

# Nexus Scout — Country-Level Real Estate Opportunity Screening (Dash/Plotly)

Nexus Scout is an interactive visual analytics tool for screening country-level real estate investment opportunities. It supports exploratory analysis and decision support through cohort-based filtering (Mode B), an interpretable 0–100 Real Estate Opportunity Score (RE_Opp), and multiple coordinated views (map, scatter, bar ranking, PCP, radar, and exact values).

---

## Project overview

The tool supports the following workflow:

- **Compute** an interpretable **RE_Opp score (0–100)** per country from a small set of socioeconomic indicators.
- **Filter** countries using meaningful **min/max value ranges** (not only percentiles).
- **Explore** results using **multiple coordinated views** on a single page (map + scatter + bar + PCP + radar + values).
- **Compare** countries using **linked selection and brushing** across views (intersection-mode brushing).

Core interaction loop:

1. Adjust filter ranges (six indicators)  
2. Press **Apply** → a filtered **cohort** is created  
3. RE_Opp scores are recomputed **within the cohort** (Mode B)  
4. Explore patterns and drill down into countries using linked views

---

## Data

This project uses a curated country dataset (e.g., `countries_master_curated.csv`) derived from the **CIA Global Statistical Database** (Kaggle):
`https://www.kaggle.com/datasets/kushagraarya10/cia-global-statistical-database`

### Entities excluded
Non-country aggregates are removed during preprocessing:
- `WORLD`
- `EUROPEAN UNION`
- `ANTARCTICA`

### Numeric cleaning
Raw values may appear as formatted strings (currency symbols, commas, units, `na`, `-`, etc.). The cleaning pipeline:
- parses numbers robustly from messy strings,
- handles missing entries,
- ensures the six target columns exist and are numeric (using `0` / `NaN` placeholders if needed).

### Six core indicators (inputs)
These are the only raw attributes used for filtering and scoring:
1. `Real_GDP_per_Capita_USD`
2. `Total_Population`
3. `Population_Growth_Rate`
4. `Net_Migration_Rate`
5. `Unemployment_Rate_percent`
6. `Public_Debt_percent_of_GDP`

---

## Scoring (RE_Opp: 0–100)

RE_Opp is a composite score based on interpretable sub-scores and explicit penalties:

**Sub-scores (0–100):**
- `Wealth_Score`
- `Demand_Score`
- `Stability_Score`
- `RE_Market_Score`

**Penalties:**
- `RE_Micro_Penalty` (discourages microstates from ranking too high due to scaling artifacts)
- `RE_DataQuality_Penalty` (proportional to missingness in the six input columns)

Final score:
- `RE_Opp = clip(base + micro_penalty + data_quality_penalty, 0, 100)`

### Mode B (cohort-based rescaling)
After the user applies filter ranges, the tool creates a **cohort** and recomputes MinMax scaling **inside that cohort**. This makes the score **relative to the current filtered subset**, enabling meaningful comparisons within the selected constraints.

If the cohort is too small (`< 2` countries), the tool avoids meaningless scaling and returns placeholder behavior (e.g., “No data”).

---

## User interface

Single-page layout with a collapsible sidebar and a main content area containing:

- **World map (choropleth):** spatial overview of RE_Opp
- **Analytics panel (tabs):**
  - **Leaderboard tab:** scatter plot + top-5 bar ranking
  - **Country drilldown tab:** PCP + radar + exact values

---

## Coordinated interaction (linked selection + brushing)

The app distinguishes:

- **Single selection:** click one country (map or scatter) → updates drilldown + highlights
- **Brushing:**
  - scatter brush → selected set of countries (lasso/box)
  - PCP brush → axis constraint ranges (`constraintrange`)

### Intersection-mode brushing (AND logic)
The “active subset” is computed as:

`Active = Cohort(filters) ∩ ScatterSelection ∩ PCPConstraints`

Brushing state is persisted in application state (e.g., via `dcc.Store`) to prevent accidental clearing during redraws (tab switching / figure refresh).

---

## File structure

### Data / pipeline
- `DataManager.py`
- `build_master_countries.py`
- `investor_config.py`
- `investor_views.py`
- `export_investor_views.py`

### UI components
- `Sidebar.py`
- `MapView.py`
- `AnalyticsPanel.py`

### Utilities
- `utils/data_processing.py`
- `utils/re_breakdown.py`
- `utils/re_scoring.py`

### Styling
- `assets/style.css`

### Optional
- `data_exploration.py` (if used for exploration/debugging)

---

## How to run (recommended order)

Run the modules in the following order:

1. `DataManager.py`  
2. `build_master_countries.py`  
3. `investor_config.py`  
4. `investor_views.py`  
5. `export_investor_views.py`  
6. `Sidebar.py`  
7. `MapView.py`  
8. `AnalyticsPanel.py`  
9. `utils/data_processing.py`  
10. `utils/re_breakdown.py`  
11. `utils/re_scoring.py`

> If your repo includes an entry point such as `Main.py`, you can typically run the app directly after the curated dataset is built.

---

## Requirements

- Python 3.x  
- Dash  
- Plotly  
- Pandas  
- NumPy  
- scikit-learn  

---

## Team Contribution Statement (Implementation vs. External Code)

This project is implemented as a Dash (Python) web application combining custom UI components, interactive Plotly visualizations, and a custom Real Estate scoring pipeline. The majority of the codebase was written by our team: we designed the dashboard structure, implemented the scoring and filtering logic, and built linking-and-brushing interactions between multiple coordinated views.

### What our team implemented (custom code)

- **Dashboard architecture**
  - Modular UI structure using `UI_Components` (e.g., `Sidebar`, `MapView`, `AnalyticsPanel`)
  - Integration in `Main.py` using Dash callbacks and application state stores

- **Data preparation pipeline**
  - Loading the curated dataset
  - Cleaning numeric fields and handling missing values
  - Removing non-country entities and producing derived features used in scoring and visualizations

- **Real Estate opportunity algorithm (custom scoring)**
  - Uses six macroeconomic attributes: GDP per capita, population, population growth, net migration, unemployment, and public debt
  - Computes interpretable components (wealth, demand, stability, market size) and combines them into a final **RE_Opp score (0–100)** with penalties (e.g., microstate and missing-data penalties)

- **Mode B interaction logic**
  - Filters countries via user-selected min/max ranges (sliders)
  - Recomputes scores within the filtered cohort (cohort-based scaling and ranking)

- **Interactive visual analytics features**
  - Choropleth world map colored by RE_Opp
  - Score-vs-attribute scatterplot (user-selected Y attribute), linked to selections and filters
  - Top-5 leaderboard bar chart updated by the active cohort/subset
  - Drilldown view with radar plot and exact values panel
  - Parallel coordinates plot (PCP) using normalized versions of the six attributes

- **Linking-and-brushing across views**
  - Scatter brushing filters the map, leaderboard, and drilldown cohort
  - PCP brushing (constraint ranges) further filters other views
  - Intersection logic combines scatter selection and PCP constraints (AND semantics)
  - Persistent single-country selection shared across map, scatter, and drilldown

### What comes from external libraries / existing tooling

- **Dash / dash-core-components** provide the web app framework, callback system, and UI primitives  
- **Plotly** provides visualization primitives (choropleth, scatter, bar, radar/polar, PCP) and built-in brushing/selection events  
- **Pandas / NumPy** are used for tabular processing and numerical operations  
- **scikit-learn (`MinMaxScaler`)** is used for normalization/scaling required by the scoring and PCP axes  
- UI styling uses standard **CSS** conventions; final rendering is handled by the browser  

In summary, our team created the data-driven scoring logic, the interactive dashboard, and the coordinated multi-view analytics behaviors, while underlying plotting and web framework capabilities are provided by widely used open-source libraries.
