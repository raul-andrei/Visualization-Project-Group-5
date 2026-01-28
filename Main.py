from dash import Dash, Input, Output, State, html, ctx, ALL, dcc
from dash.exceptions import PreventUpdate

from UI_Components.Sidebar import Sidebar
from UI_Components.MapView import MapView
from UI_Components.AnalyticsPanel import AnalyticsPanel

from UTILS.data_processing import load_and_process_data
from UTILS.re_scoring import (
    compute_real_estate_scores,
    filter_and_score_real_estate_cohort,
)

from plotly import express as px
from plotly import graph_objects as go

import numpy as np
import pandas as pd


# -----------------------------
# Data
# -----------------------------
scoring_df = load_and_process_data()

# -----------------------------
# Styling
# -----------------------------
GREEN_SCALE = [
    [0.00, "#0b1311"],
    [0.10, "#10231f"],
    [0.20, "#163a33"],
    [0.35, "#1f5c52"],
    [0.50, "#2a7f72"],
    [0.65, "#38a89a"],
    [0.80, "#4fd1c5"],
    [0.90, "#66fcf1"],
    [1.00, "#8ffdf4"],
]

# Short labels (prevents stacked text in SPLOM/PCP)

SHORT_LABELS = {
    "GDP per Capita (USD)": "GDP/cap",
    "Population": "Pop",
    "Population Growth (%)": "Pop Growth",
    "Net Migration Rate": "Migration",
    "Unemployment (%)": "Unemp",
    "Public Debt (% of GDP)": "Debt",
    "Agricultural Area (km²)": "Ag Area",
    "Irrigated Land (km²)": "Irrigation",
    "Exports (B USD)": "Exports",
    "Imports (B USD)": "Imports",
    "Ag Area per Capita": "Ag/cap",
    "Roadways (km)": "Roads",
    "Railways (km)": "Rails",
    "Airports (paved runways)": "Airports",
    "Coastline (km)": "Coast",
    "Internet Penetration": "Internet",
    "Mobile Penetration": "Mobile",
    "Broadband Penetration": "Broadband",
    "Electricity Capacity (kW)": "Electricity",
    "Internet Users (Scale)": "Users",
    "Broadband Subs (Scale)": "Broad Subs",
    "GDP Growth (%)": "GDP Growth",
}

# Scatter Y options for the score-vs-attribute scatter plot
SCATTER_Y_OPTIONS = [
    {"col": "Real_GDP_per_Capita_USD", "label": "GDP per Capita", "unit": "k USD", "scale": 1_000.0},
    {"col": "Total_Population", "label": "Population", "unit": "M people", "scale": 1_000_000.0},
    {"col": "Population_Growth_Rate", "label": "Population Growth", "unit": "%", "scale": 1.0},
    {"col": "Net_Migration_Rate", "label": "Net Migration", "unit": "", "scale": 1.0},
    {"col": "Unemployment_Rate_percent", "label": "Unemployment", "unit": "%", "scale": 1.0},
    {"col": "Public_Debt_percent_of_GDP", "label": "Public Debt", "unit": "% of GDP", "scale": 1.0},
]


class Main:
    def __init__(self):
        self.app = Dash(__name__, suppress_callback_exceptions=True)
        self.app.title = "NEXUS SCOUT"

        self.sidebar = Sidebar()
        self.map_view = MapView()
        self.analytics_panel = AnalyticsPanel()

        self.INVESTOR_LABEL = "REAL ESTATE"
        self.app.layout = self.setup_layout()

        # Force Plotly to relayout smoothly during sidebar collapse/expand
        self.app.clientside_callback(
            """
            function(state) {
                const delays = [0, 50, 120, 200, 300, 420];
                delays.forEach(d => setTimeout(() => window.dispatchEvent(new Event('resize')), d));
                return Date.now();
            }
            """,
            Output("plotly-resize-signal", "data"),
            Input("sidebar-state", "data"),
        )

        self.register_callbacks()

    # ---------- Utils ----------
    def _empty_world_figure(self):
        fig = go.Figure(go.Scattergeo())
        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            geo=dict(
                bgcolor="rgba(0,0,0,0)",
                showland=True,
                landcolor="#1f2833",
                showocean=True,
                oceancolor="#0b0c10",
                showcountries=True,
                countrycolor="#45a29e",
                projection_type="natural earth",
            ),
            dragmode=False,
        )
        return fig

    def _dark_fig_layout(self, fig: go.Figure, title: str = None):
        if title:
            fig.update_layout(title=title)

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="white"),
            margin=dict(l=10, r=10, t=60, b=10),
        )
        fig.update_xaxes(
            color="white",
            gridcolor="rgba(255,255,255,0.08)",
            zerolinecolor="rgba(255,255,255,0.12)",
        )
        fig.update_yaxes(
            color="white",
            gridcolor="rgba(255,255,255,0.08)",
            zerolinecolor="rgba(255,255,255,0.12)",
        )
        return fig


    def _empty_message_fig(self, text: str):
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=10, r=10, t=10, b=10),
            annotations=[
                dict(
                    text=text,
                    showarrow=False,
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    font=dict(color="white", size=14),
                )
            ],
        )
        return fig

    def _subset_nearest(
        self,
        scored_df: pd.DataFrame,
        selected_country: str,
        score_col: str,
        n: int = 60,
    ) -> pd.DataFrame:
        selected_country = str(selected_country)

        if "PCA_1" in scored_df.columns and "PCA_2" in scored_df.columns:
            hit = scored_df[scored_df["Country"].astype(str) == selected_country]
            if not hit.empty:
                x0 = float(hit.iloc[0]["PCA_1"])
                y0 = float(hit.iloc[0]["PCA_2"])
                df2 = scored_df.copy()
                df2["_dist"] = (df2["PCA_1"].astype(float) - x0) ** 2 + (df2["PCA_2"].astype(float) - y0) ** 2
                df2 = df2.sort_values("_dist", ascending=True)
                sub = df2.head(n + 1).drop(columns=["_dist"], errors="ignore")
                return sub

        sub = scored_df.sort_values(score_col, ascending=False).head(n).copy()
        if selected_country not in sub["Country"].astype(str).values:
            hit = scored_df[scored_df["Country"].astype(str) == selected_country]
            if not hit.empty:
                sub = pd.concat([hit, sub], ignore_index=True).drop_duplicates(subset=["Country"])
        return sub

    def _safe_numeric_series(self, s: pd.Series, default: float = 0.0) -> pd.Series:
        return (
            pd.to_numeric(s, errors="coerce")
            .replace([np.inf, -np.inf], np.nan)
            .fillna(default)
        )

    # ---------- Filtering + Mode-B scoring ----------
    def _filters_from_ranges(self, values_list, ids_list):
        """Convert pattern-matching RangeSlider values into a {col: (min,max)} dict."""
        if not values_list or not ids_list:
            return {}

        out = {}
        for v, i in zip(values_list, ids_list):
            col = str(i.get("col"))
            if isinstance(v, (list, tuple)) and len(v) == 2:
                out[col] = (v[0], v[1])
        return out

    def _score_mode_b(self, base_df: pd.DataFrame, filters: dict) -> pd.DataFrame:
        """Apply Mode-B cohort filtering + re-scoring using `filter_and_score_real_estate_cohort`.

        IMPORTANT:
        The UI RangeSliders now operate on *human-friendly units*:
        - GDP per Capita slider is in **k USD** (e.g., 55 -> $55,000)
        - Population slider is in **M people** (e.g., 20 -> 20,000,000)
        - Growth/Unemployment/Debt sliders are in **%**
        - Net Migration slider uses the dataset's raw units

        We convert those slider bounds into the raw numeric bounds expected by the cohort filter.
        """

        def _get(col):
            return filters.get(col, (None, None))

        def _as_float_pair(v):
            if not isinstance(v, (list, tuple)) or len(v) != 2:
                return None, None
            try:
                return float(v[0]), float(v[1])
            except Exception:
                return None, None

        def _bounds_raw(col: str, lo, hi):
            """Convert slider bounds -> raw bounds for a specific column."""
            lo_f, hi_f = _as_float_pair([lo, hi])
            if lo_f is None or hi_f is None:
                return None, None

            # Ensure ordering
            if lo_f > hi_f:
                lo_f, hi_f = hi_f, lo_f

            # Unit conversions
            if col == "Total_Population":
                lo_f *= 1_000_000.0
                hi_f *= 1_000_000.0
            elif col == "Real_GDP_per_Capita_USD":
                lo_f *= 1_000.0
                hi_f *= 1_000.0
            # Percent-based columns: already in % (no conversion)
            # Migration: keep raw

            return lo_f, hi_f

        # Slider bounds -> raw bounds
        gdp_lo, gdp_hi = _bounds_raw("Real_GDP_per_Capita_USD", *_get("Real_GDP_per_Capita_USD"))
        pop_lo, pop_hi = _bounds_raw("Total_Population", *_get("Total_Population"))
        pg_lo, pg_hi = _bounds_raw("Population_Growth_Rate", *_get("Population_Growth_Rate"))
        mig_lo, mig_hi = _bounds_raw("Net_Migration_Rate", *_get("Net_Migration_Rate"))
        un_lo, un_hi = _bounds_raw("Unemployment_Rate_percent", *_get("Unemployment_Rate_percent"))
        debt_lo, debt_hi = _bounds_raw("Public_Debt_percent_of_GDP", *_get("Public_Debt_percent_of_GDP"))

        return filter_and_score_real_estate_cohort(
            base_df,
            gdp_per_capita_min=gdp_lo,
            gdp_per_capita_max=gdp_hi,
            population_min=pop_lo,
            population_max=pop_hi,
            pop_growth_min=pg_lo,
            pop_growth_max=pg_hi,
            net_migration_min=mig_lo,
            net_migration_max=mig_hi,
            unemployment_min=un_lo,
            unemployment_max=un_hi,
            debt_min=debt_lo,
            debt_max=debt_hi,
            max_missing=1,
            keep_intermediate=True,
            missing_penalty_enabled=True,
            missing_penalty_max=15.0,
        )

    def _normalize_0_100(self, df: pd.DataFrame, col: str, invert: bool = False) -> pd.Series:
        """Min-max normalize a column to 0..100 within the given df."""
        s = self._safe_numeric_series(df[col], default=np.nan)
        mn = float(np.nanmin(s.to_numpy(dtype=float))) if np.isfinite(np.nanmin(s.to_numpy(dtype=float))) else 0.0
        mx = float(np.nanmax(s.to_numpy(dtype=float))) if np.isfinite(np.nanmax(s.to_numpy(dtype=float))) else 1.0
        if mx - mn < 1e-12:
            out = np.zeros(len(df), dtype=float)
        else:
            out = (s.to_numpy(dtype=float) - mn) / (mx - mn) * 100.0
        if invert:
            out = 100.0 - out
        return pd.Series(out, index=df.index)

    # ---------- Callbacks ----------
    def register_callbacks(self):

        # -----------------------------
        # Sidebar state: collapse only
        # -----------------------------
        @self.app.callback(
            Output("sidebar-state", "data"),
            Input("sidebar-collapse-btn", "n_clicks"),
            State("sidebar-state", "data"),
            prevent_initial_call=True,
        )
        def update_sidebar_state(collapse_clicks, state):
            if state is None:
                state = {"collapsed": False}

            if ctx.triggered_id != "sidebar-collapse-btn":
                raise PreventUpdate

            state["collapsed"] = not state.get("collapsed", False)
            return state

        @self.app.callback(
            Output("sidebar-wrapper", "className"),
            Output("map-and-analytics-container", "className"),
            Input("sidebar-state", "data"),
        )
        def apply_sidebar_classes(state):
            if not state:
                state = {"collapsed": False}

            collapsed = state.get("collapsed", False)

            sidebar_class = "sidebar sidebar--collapsed" if collapsed else "sidebar"
            content_class = (
                "map-and-analytics-container map-and-analytics-container--collapsed"
                if collapsed
                else "map-and-analytics-container"
            )
            return sidebar_class, content_class

        # -----------------------------
        # Filter range display (min/max shown next to each slider)
        # Expects RangeSliders with id={"type": "filter-slider", "col": <col>}
        # and a label span with id={"type": "filter-value", "col": <col>}
        # -----------------------------
        @self.app.callback(
            Output({"type": "filter-range-value", "col": ALL}, "children"),
            Input({"type": "filter-range", "col": ALL}, "value"),
            State({"type": "filter-range", "col": ALL}, "id"),
            prevent_initial_call=False,
        )
        def render_filter_range_labels(values_list, ids_list):
            if not values_list or not ids_list:
                return []

            def _fmt(col: str, x):
                try:
                    xf = float(x)
                except Exception:
                    return str(x)

                if abs(xf - round(xf)) < 1e-9:
                    xf_str = str(int(round(xf)))
                else:
                    xf_str = f"{xf:.2f}"

                if col == "Total_Population":
                    return f"{xf_str}M"
                if col == "Real_GDP_per_Capita_USD":
                    return f"{xf_str}k"
                if col in {"Population_Growth_Rate", "Unemployment_Rate_percent", "Public_Debt_percent_of_GDP"}:
                    return f"{xf_str}%"
                return xf_str

            labels = []
            for v, i in zip(values_list, ids_list):
                col = str(i.get("col"))
                if isinstance(v, (list, tuple)) and len(v) == 2:
                    lo, hi = v
                    labels.append(f"{_fmt(col, lo)}–{_fmt(col, hi)}")
                else:
                    labels.append(str(v))

            return labels

        # -----------------------------
        # Apply filters (snapshot RangeSlider values when Apply is clicked)
        # -----------------------------
        @self.app.callback(
            Output("filters-applied-store", "data"),
            Input("apply-weights-btn", "n_clicks"),
            State({"type": "filter-range", "col": ALL}, "value"),
            State({"type": "filter-range", "col": ALL}, "id"),
            prevent_initial_call=True,
        )
        def apply_filters(n_clicks, values_list, ids_list):
            if not n_clicks:
                raise PreventUpdate
            filters = self._filters_from_ranges(values_list, ids_list)
            return filters

        # -----------------------------
        # Map updates (Mode-B)
        # -----------------------------
        @self.app.callback(
            Output("world-map", "figure"),
            Input("filters-applied-store", "data"),
        )
        def update_map(filters_applied):
            filters_applied = filters_applied or {}

            try:
                scored_df = self._score_mode_b(scoring_df, filters_applied)
            except Exception:
                # Fallback to global scoring if cohort scoring fails
                try:
                    scored_df = compute_real_estate_scores(scoring_df, fit_df=scoring_df, keep_intermediate=True)
                except Exception:
                    return self._empty_world_figure()

            score_col = "RE_Opp"
            df_plot = scored_df[["Country", score_col]].dropna()
            if df_plot.empty:
                return self._empty_world_figure()

            fig = px.choropleth(
                df_plot,
                locations="Country",
                locationmode="country names",
                color=score_col,
                hover_name="Country",
                title=None,
                color_continuous_scale=GREEN_SCALE,
                range_color=(0, 100),
            )

            fig.update_traces(
                marker_line_width=1.5,
                marker_line_color="rgba(255,255,255,0.15)",
            )

            fig.update_layout(
                title_font=dict(family="Inter, sans-serif", size=22, color="white"),
                font=dict(family="Inter, sans-serif", color="white"),
                margin={"r": 0, "t": 60, "l": 0, "b": 0},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                geo=dict(
                    bgcolor="rgba(0,0,0,0)",
                    showland=True,
                    landcolor="#1f2833",
                    showocean=True,
                    oceancolor="#0b0c10",
                    showcountries=True,
                    countrycolor="#45a29e",
                    projection_type="natural earth",
                ),
                font_color="white",
            )

            return fig

        # -----------------------------
        # Top 5 (Mode-B)
        # -----------------------------
        @self.app.callback(
            Output("top-5-chart", "children"),
            Input("filters-applied-store", "data"),
        )
        def top5(filters_applied):
            filters_applied = filters_applied or {}

            try:
                scored_df = self._score_mode_b(scoring_df, filters_applied)
            except Exception:
                try:
                    scored_df = compute_real_estate_scores(scoring_df, fit_df=scoring_df, keep_intermediate=True)
                except Exception:
                    return "No data"

            score_col = "RE_Opp"
            df_top = scored_df[["Country", score_col]].dropna().nlargest(5, score_col)
            if df_top.empty:
                return "No data"

            bar_fig = px.bar(
                df_top,
                x="Country",
                y=score_col,
                title=None,
                color_discrete_sequence=["#1f5c52"],
            )
            bar_fig = self._dark_fig_layout(bar_fig)
            bar_fig.update_yaxes(range=[0, 100])
            bar_fig.update_yaxes(title="Real Estate Opportunity Score (0–100)")
            return dcc.Graph(figure=bar_fig, config={"displayModeBar": False})

        # -----------------------------
        # Score vs Attribute Scatter: dropdown options
        # -----------------------------
        @self.app.callback(
            Output("scatter-y-attr", "options"),
            Input("plotly-resize-signal", "data"),
            prevent_initial_call=False,
        )
        def _init_scatter_dropdown(_):
            return [{"label": o["label"], "value": o["col"]} for o in SCATTER_Y_OPTIONS]

        # -----------------------------
        # Score vs Attribute Scatter: main figure
        # -----------------------------
        @self.app.callback(
            Output("score-attr-scatter", "figure"),
            Input("filters-applied-store", "data"),
            Input("scatter-y-attr", "value"),
        )
        def update_score_attr_scatter(filters_applied, y_col):
            filters_applied = filters_applied or {}
            y_col = y_col or "Real_GDP_per_Capita_USD"

            # Lookup label/unit/scale
            meta = next((o for o in SCATTER_Y_OPTIONS if o["col"] == y_col), None)
            if meta is None:
                meta = {"col": y_col, "label": y_col, "unit": "", "scale": 1.0}

            try:
                scored_df = self._score_mode_b(scoring_df, filters_applied)
            except Exception:
                try:
                    scored_df = compute_real_estate_scores(scoring_df, fit_df=scoring_df, keep_intermediate=True)
                except Exception:
                    return self._empty_message_fig("No data")

            if scored_df is None or len(scored_df) == 0 or y_col not in scored_df.columns:
                return self._empty_message_fig("No data")

            dfp = scored_df[["Country", "RE_Opp", y_col]].copy()
            dfp["RE_Opp"] = self._safe_numeric_series(dfp["RE_Opp"], default=np.nan)
            dfp[y_col] = self._safe_numeric_series(dfp[y_col], default=np.nan)
            dfp = dfp.dropna(subset=["RE_Opp", y_col])
            if dfp.empty:
                return self._empty_message_fig("No data")

            # Scale Y for readability
            y_scaled = dfp[y_col] / float(meta.get("scale", 1.0) or 1.0)
            y_title = meta["label"] + (f" ({meta['unit']})" if meta.get("unit") else "")

            fig = px.scatter(
                dfp.assign(_y=y_scaled),
                x="RE_Opp",
                y="_y",
                hover_name="Country",
                title=f"Score vs {meta['label']}",
                color_discrete_sequence=["#38a89a"],
            )

            fig.update_traces(marker=dict(size=7, opacity=0.65))

            fig.update_layout(
                title_font=dict(family="Inter, sans-serif", size=16, color="white"),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", color="white"),
                margin=dict(l=10, r=10, t=50, b=10),
                showlegend=False,
            )

            fig.update_xaxes(
                title="Real Estate Opportunity Score (0–100)",
                range=[0, 100],
                color="white",
                gridcolor="rgba(255,255,255,0.08)",
                zerolinecolor="rgba(255,255,255,0.12)",
            )

            fig.update_yaxes(
                title=y_title,
                color="white",
                gridcolor="rgba(255,255,255,0.08)",
                zerolinecolor="rgba(255,255,255,0.12)",
            )

            return fig

        # -----------------------------
        # Country click -> store
        # -----------------------------
        @self.app.callback(
            Output("selected-country-store", "data"),
            Input("world-map", "clickData"),
            prevent_initial_call=True,
        )
        def set_country_store(clickData):
            if not clickData or "points" not in clickData or not clickData["points"]:
                raise PreventUpdate

            p = clickData["points"][0]
            if p.get("location"):
                return str(p["location"])
            if p.get("text"):
                return str(p["text"])
            raise PreventUpdate

        # -----------------------------
        # Drilldown: SPLOM + PCP (CLEAN VERSION)
        # -----------------------------
        @self.app.callback(
            Output("drilldown-country-title", "children"),
            Output("drilldown-investor-label", "children"),
            Output("drilldown-splom", "figure"),
            Output("drilldown-pcp", "figure"),
            Input("selected-country-store", "data"),
            Input("filters-applied-store", "data"),
        )
        def render_country_drilldown(selected_country, filters_applied):
            try:
                investor_label = self.INVESTOR_LABEL
                filters_applied = filters_applied or {}

                if not selected_country:
                    return (
                        "Click a country on the map",
                        investor_label,
                        self._empty_message_fig("Click a country to show SPLOM."),
                        self._empty_message_fig("Click a country to show PCP."),
                    )

                # Score the current cohort (Mode B) so drilldown matches the filtered view
                try:
                    scored_df = self._score_mode_b(scoring_df, filters_applied)
                except Exception:
                    scored_df = compute_real_estate_scores(scoring_df, fit_df=scoring_df, keep_intermediate=True)

                score_col = "RE_Opp"

                hit = scored_df[scored_df["Country"].astype(str) == str(selected_country)]
                if hit.empty:
                    msg = f"Country not found: {selected_country}"
                    return msg, investor_label, self._empty_message_fig(msg), self._empty_message_fig(msg)

                # Comparison set
                df_sub = self._subset_nearest(scored_df, str(selected_country), score_col, n=60).copy()

                # Use the 6 RE input attributes for multivariate views
                raw_cols = [
                    ("Real_GDP_per_Capita_USD", "GDP/cap", False),
                    ("Total_Population", "Pop", False),
                    ("Population_Growth_Rate", "Pop Growth", False),
                    ("Net_Migration_Rate", "Migration", False),
                    ("Unemployment_Rate_percent", "Unemp", True),
                    ("Public_Debt_percent_of_GDP", "Debt", True),
                ]

                labels = []
                for col, lab, inv in raw_cols:
                    if col not in df_sub.columns:
                        df_sub[col] = np.nan
                    df_sub[lab] = self._normalize_0_100(df_sub, col, invert=inv)
                    labels.append(lab)

                df_sub[score_col] = self._safe_numeric_series(df_sub.get(score_col, 0.0), default=0.0).clip(0, 100)

                title = f"{selected_country} — {investor_label} | Compare: {len(df_sub)}"

                # ---------- SPLOM ----------
                splom_fig = px.scatter_matrix(
                    df_sub,
                    dimensions=labels,
                    color=score_col,
                    hover_name="Country",
                    color_continuous_scale=GREEN_SCALE,
                )

                splom_fig.update_traces(
                    diagonal_visible=False,
                    showupperhalf=False,
                    showlowerhalf=True,
                    marker=dict(size=5, opacity=0.55),
                )

                sel_mask = df_sub["Country"].astype(str).values == str(selected_country)
                if len(splom_fig.data) > 0:
                    sizes = np.where(sel_mask, 12, 5)
                    splom_fig.data[0].update(marker=dict(size=sizes, opacity=0.65))

                splom_fig.update_layout(
                    title=None,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter, sans-serif", color="white", size=11),
                    margin=dict(l=10, r=10, t=10, b=10),
                    coloraxis_showscale=False,
                )
                splom_fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.06)")
                splom_fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.06)")

                # ---------- PCP ----------
                df_sub_sorted = df_sub.sort_values(score_col, ascending=False).copy()
                top = df_sub_sorted.head(20)
                bottom = df_sub_sorted.tail(10)
                sel = df_sub_sorted[df_sub_sorted["Country"].astype(str) == str(selected_country)]
                pcp_df = pd.concat([top, bottom, sel], ignore_index=True).drop_duplicates(subset=["Country"])

                dims = [
                    dict(label=lab, range=[0, 100], values=self._safe_numeric_series(pcp_df[lab], 0.0).values)
                    for lab in labels
                ]

                pcp_fig = go.Figure()
                pcp_fig.add_trace(
                    go.Parcoords(
                        line=dict(
                            color=self._safe_numeric_series(pcp_df[score_col], 0.0).values,
                            colorscale=GREEN_SCALE,
                            cmin=float(pcp_df[score_col].min()),
                            cmax=float(pcp_df[score_col].max()),
                            showscale=True,
                        ),
                        dimensions=dims,
                        labelfont=dict(color="white", size=12),
                        tickfont=dict(color="rgba(255,255,255,0.7)", size=10),
                    )
                )

                df_sel = pcp_df[pcp_df["Country"].astype(str) == str(selected_country)]
                if not df_sel.empty:
                    dims_sel = [
                        dict(label=lab, range=[0, 100], values=self._safe_numeric_series(df_sel[lab], 0.0).values)
                        for lab in labels
                    ]
                    pcp_fig.add_trace(
                        go.Parcoords(
                            line=dict(
                                color=[1.0] * len(df_sel),
                                colorscale=[[0, "#66fcf1"], [1, "#66fcf1"]],
                                cmin=0.0,
                                cmax=1.0,
                                showscale=False,
                            ),
                            dimensions=dims_sel,
                            labelfont=dict(color="white", size=12),
                            tickfont=dict(color="rgba(255,255,255,0.8)", size=10),
                        )
                    )

                pcp_fig.update_layout(
                    title=None,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter, sans-serif", color="white"),
                    margin=dict(l=10, r=10, t=10, b=10),
                )

                return title, investor_label, splom_fig, pcp_fig

            except Exception as e:
                msg = f"Drilldown error: {type(e).__name__}: {e}"
                investor_label = self.INVESTOR_LABEL
                return msg, investor_label, self._empty_message_fig(msg), self._empty_message_fig(msg)

    # ---------- Layout ----------
    def setup_layout(self):
        return html.Div(
            className="app-container",
            children=[
                dcc.Store(id="sidebar-state", data={"collapsed": False}),
                dcc.Store(id="plotly-resize-signal", data=0),

                # Selection state
                dcc.Store(id="selected-country-store", storage_type="memory"),
                dcc.Store(id="filters-applied-store", storage_type="memory"),

                self.sidebar.render(),

                html.Div(
                    id="map-and-analytics-container",
                    className="map-and-analytics-container",
                    children=[
                        self.map_view.render(),
                        self.analytics_panel.render(),
                    ],
                ),
            ],
        )

    def run(self):
        self.app.run(debug=True, dev_tools_ui=False)


if __name__ == "__main__":
    main = Main()
    main.run()

