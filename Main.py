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

DIM_GREEN_SCALE = [
    [0.00, "rgba(11,19,17,0.18)"],
    [0.10, "rgba(16,35,31,0.18)"],
    [0.20, "rgba(22,58,51,0.18)"],
    [0.35, "rgba(31,92,82,0.18)"],
    [0.50, "rgba(42,127,114,0.18)"],
    [0.65, "rgba(56,168,154,0.18)"],
    [0.80, "rgba(79,209,197,0.18)"],
    [0.90, "rgba(102,252,241,0.18)"],
    [1.00, "rgba(143,253,244,0.18)"],
]

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
            uirevision="world-map",
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

    def _subset_nearest(self, scored_df: pd.DataFrame, selected_country: str, score_col: str, n: int = 60) -> pd.DataFrame:
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
        if not values_list or not ids_list:
            return {}
        out = {}
        for v, i in zip(values_list, ids_list):
            col = str(i.get("col"))
            if isinstance(v, (list, tuple)) and len(v) == 2:
                out[col] = (v[0], v[1])
        return out

    def _score_mode_b(self, base_df: pd.DataFrame, filters: dict) -> pd.DataFrame:
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
            lo_f, hi_f = _as_float_pair([lo, hi])
            if lo_f is None or hi_f is None:
                return None, None
            if lo_f > hi_f:
                lo_f, hi_f = hi_f, lo_f

            # slider units -> raw units
            if col == "Total_Population":
                lo_f *= 1_000_000.0
                hi_f *= 1_000_000.0
            elif col == "Real_GDP_per_Capita_USD":
                lo_f *= 1_000.0
                hi_f *= 1_000.0

            return lo_f, hi_f

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
        s = self._safe_numeric_series(df[col], default=np.nan)
        arr = s.to_numpy(dtype=float)

        if np.all(~np.isfinite(arr)):
            out = np.zeros(len(df), dtype=float)
        else:
            mn = float(np.nanmin(arr))
            mx = float(np.nanmax(arr))
            if mx - mn < 1e-12:
                out = np.zeros(len(df), dtype=float)
            else:
                out = (arr - mn) / (mx - mn) * 100.0

        if invert:
            out = 100.0 - out
        return pd.Series(out, index=df.index)

    def _add_re_norm_axes(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        raw_cols = [
            ("Real_GDP_per_Capita_USD", "GDP/cap", False),
            ("Total_Population", "Pop", False),
            ("Population_Growth_Rate", "Pop Growth", False),
            ("Net_Migration_Rate", "Migration", False),
            ("Unemployment_Rate_percent", "Unemp", True),
            ("Public_Debt_percent_of_GDP", "Debt", True),
        ]
        for col, lab, inv in raw_cols:
            if col not in out.columns:
                out[col] = np.nan
            out[lab] = self._normalize_0_100(out, col, invert=inv)
        return out

    def _fmt_raw_value(self, col: str, x):
        if x is None or (isinstance(x, float) and not np.isfinite(x)):
            return "—"
        try:
            xf = float(x)
        except Exception:
            return str(x)

        if col == "Real_GDP_per_Capita_USD":
            return f"${xf:,.0f}"
        if col == "Total_Population":
            return f"{xf:,.0f}"
        if col in {"Population_Growth_Rate", "Unemployment_Rate_percent", "Public_Debt_percent_of_GDP"}:
            return f"{xf:.2f}%"
        if col == "Net_Migration_Rate":
            return f"{xf:.2f}"
        return f"{xf:.2f}"

    # ---------- Helper: apply PCP constraints ----------
    def _apply_constraints(self, df: pd.DataFrame, constraints: dict) -> pd.DataFrame:
        if not constraints:
            return df

        def _in_ranges(x, r):
            if x is None or (isinstance(x, float) and not np.isfinite(x)):
                return False
            try:
                xf = float(x)
            except Exception:
                return False

            if isinstance(r, (list, tuple)) and len(r) == 2 and not isinstance(r[0], (list, tuple)):
                lo, hi = r
                return float(lo) <= xf <= float(hi)

            if isinstance(r, (list, tuple)) and len(r) > 0 and isinstance(r[0], (list, tuple)):
                for seg in r:
                    if isinstance(seg, (list, tuple)) and len(seg) == 2:
                        lo, hi = seg
                        if float(lo) <= xf <= float(hi):
                            return True
                return False

            return True

        mask = np.ones(len(df), dtype=bool)
        for lab, r in constraints.items():
            if lab not in df.columns:
                continue
            colvals = df[lab].values
            mask &= np.array([_in_ranges(v, r) for v in colvals], dtype=bool)

        return df.loc[mask].copy()

    def _apply_intersection(self, scored_df: pd.DataFrame, scatter_store: dict, pcp_store: dict) -> pd.DataFrame:
        df = scored_df.copy()

        scatter_countries = []
        if scatter_store and isinstance(scatter_store, dict):
            scatter_countries = scatter_store.get("countries", []) or []
        if scatter_countries:
            df = df[df["Country"].astype(str).isin([str(c) for c in scatter_countries])].copy()

        constraints = {}
        if pcp_store and isinstance(pcp_store, dict):
            constraints = pcp_store.get("constraints", {}) or {}
        if constraints:
            df = self._add_re_norm_axes(df)
            df = self._apply_constraints(df, constraints)

        return df

    # ---------- Callbacks ----------
    def register_callbacks(self):

        # Sidebar collapse state
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

        # Filter range display labels
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

            labels_out = []
            for v, i in zip(values_list, ids_list):
                col = str(i.get("col"))
                if isinstance(v, (list, tuple)) and len(v) == 2:
                    lo, hi = v
                    labels_out.append(f"{_fmt(col, lo)}–{_fmt(col, hi)}")
                else:
                    labels_out.append(str(v))
            return labels_out

        # Apply filters snapshot
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

        # Keep map camera stable
        @self.app.callback(
            Output("world-map-view-store", "data"),
            Input("world-map", "relayoutData"),
            State("world-map-view-store", "data"),
            prevent_initial_call=True,
        )
        def store_map_view(relayoutData, current):
            if not isinstance(relayoutData, dict):
                raise PreventUpdate

            allowed_keys = {
                "geo.center",
                "geo.center.lon",
                "geo.center.lat",
                "geo.projection.scale",
                "geo.lonaxis.range",
                "geo.lataxis.range",
            }
            keep = {k: v for k, v in relayoutData.items() if k in allowed_keys}

            if not keep:
                raise PreventUpdate

            merged = dict(current or {})
            merged.update(keep)
            return merged

        # Country selection from MAP OR SCATTER (toggle off on same country)
        @self.app.callback(
            Output("selected-country-store", "data"),
            Input("world-map", "clickData"),
            Input("score-attr-scatter", "clickData"),
            State("selected-country-store", "data"),
            prevent_initial_call=True,
        )
        def set_country_store(map_click, scatter_click, current_selected):
            trig = ctx.triggered_id

            if trig == "world-map":
                if not map_click or "points" not in map_click or not map_click["points"]:
                    raise PreventUpdate
                p = map_click["points"][0]
                clicked = str(p.get("location") or p.get("text") or "")
                if not clicked:
                    raise PreventUpdate
                if current_selected and str(current_selected) == clicked:
                    return None
                return clicked

            if trig == "score-attr-scatter":
                if not scatter_click or "points" not in scatter_click or not scatter_click["points"]:
                    raise PreventUpdate
                p = scatter_click["points"][0]
                clicked = str(p.get("hovertext") or p.get("text") or "")
                if not clicked:
                    raise PreventUpdate
                if current_selected and str(current_selected) == clicked:
                    return None
                return clicked

            raise PreventUpdate

        # MAP updates + highlight selected country (filtered by scatter + pcp)
        @self.app.callback(
            Output("world-map", "figure"),
            Input("filters-applied-store", "data"),
            Input("selected-country-store", "data"),
            Input("scatter-brush-store", "data"),
            Input("pcp-brush-store", "data"),
            State("world-map-view-store", "data"),
        )
        def update_map(filters_applied, selected_country, scatter_store, pcp_store, map_view_store):
            filters_applied = filters_applied or {}

            try:
                scored_df = self._score_mode_b(scoring_df, filters_applied)
            except Exception:
                try:
                    scored_df = compute_real_estate_scores(scoring_df, fit_df=scoring_df, keep_intermediate=True)
                except Exception:
                    return self._empty_world_figure()

            scored_df = self._apply_intersection(scored_df, scatter_store, pcp_store)

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
            fig.update_traces(marker_line_width=1.5, marker_line_color="rgba(255,255,255,0.15)")

            if selected_country:
                df_sel = df_plot[df_plot["Country"].astype(str) == str(selected_country)]
                if not df_sel.empty:
                    fig.add_trace(
                        go.Choropleth(
                            locations=df_sel["Country"],
                            locationmode="country names",
                            z=[1] * len(df_sel),
                            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                            showscale=False,
                            marker_line_width=4,
                            marker_line_color="#66fcf1",
                            hoverinfo="skip",
                        )
                    )

            fig.update_layout(
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
                font=dict(family="Inter, sans-serif", color="white"),
                uirevision="world-map",
            )

            if isinstance(map_view_store, dict) and map_view_store:
                fig.update_layout(**map_view_store)

            return fig

        # Top 5 (filtered by scatter + pcp)
        @self.app.callback(
            Output("top-5-chart", "children"),
            Input("filters-applied-store", "data"),
            Input("scatter-brush-store", "data"),
            Input("pcp-brush-store", "data"),
        )
        def top5(filters_applied, scatter_store, pcp_store):
            filters_applied = filters_applied or {}
            try:
                scored_df = self._score_mode_b(scoring_df, filters_applied)
            except Exception:
                try:
                    scored_df = compute_real_estate_scores(scoring_df, fit_df=scoring_df, keep_intermediate=True)
                except Exception:
                    return "No data"

            scored_df = self._apply_intersection(scored_df, scatter_store, pcp_store)

            score_col = "RE_Opp"
            df_top = scored_df[["Country", score_col]].dropna().nlargest(5, score_col)
            if df_top.empty:
                return "No data"

            bar_fig = px.bar(df_top, x="Country", y=score_col, title=None, color_discrete_sequence=["#1f5c52"])
            bar_fig = self._dark_fig_layout(bar_fig)
            bar_fig.update_yaxes(range=[0, 100], title="Real Estate Opportunity Score (0–100)")
            return dcc.Graph(figure=bar_fig, config={"displayModeBar": False})

        # Scatter dropdown init
        @self.app.callback(
            Output("scatter-y-attr", "options"),
            Input("plotly-resize-signal", "data"),
            prevent_initial_call=False,
        )
        def _init_scatter_dropdown(_):
            return [{"label": o["label"], "value": o["col"]} for o in SCATTER_Y_OPTIONS]

        # Scatter brushing -> store selected countries
        # Clear ONLY on double-click reset; ignore redraw noise.
        @self.app.callback(
            Output("scatter-brush-store", "data", allow_duplicate=True),
            Input("score-attr-scatter", "selectedData"),
            Input("score-attr-scatter", "relayoutData"),
            State("scatter-brush-store", "data"),
            prevent_initial_call=True,
        )
        def store_scatter_brush(selectedData, relayoutData, current_store):
            current_store = current_store or {"countries": []}

            def _is_resize_noise(r):
                return isinstance(r, dict) and (r.get("autosize") is True or "width" in r or "height" in r)

            def _is_reset_signal(r):
                if not isinstance(r, dict):
                    return False
                # Most reliable: autorange on either axis
                if r.get("xaxis.autorange") is True or r.get("yaxis.autorange") is True:
                    return True
                # Some versions: selection cleared via selections=[]
                if r.get("selections") == [] or r.get("selections") is None:
                    return True
                return False

            # Clear brush on reset (and NOT on resize noise)
            if _is_reset_signal(relayoutData) and not _is_resize_noise(relayoutData):
                if current_store.get("countries"):
                    return {"countries": []}
                return {"countries": []}

            # Update store on real selection points
            if not isinstance(selectedData, dict) or "points" not in selectedData:
                raise PreventUpdate

            pts = selectedData.get("points") or []
            if len(pts) == 0:
                # usually redraw noise; real clear handled above
                raise PreventUpdate

            countries = []
            for p in pts:
                c = p.get("hovertext") or p.get("text")
                if c:
                    countries.append(str(c))

            seen = set()
            uniq = []
            for c in countries:
                if c not in seen:
                    seen.add(c)
                    uniq.append(c)

            return {"countries": uniq}

        # ALSO clear PCP constraints when scatter resets (so map/leaderboard fully return)
        @self.app.callback(
            Output("pcp-brush-store", "data", allow_duplicate=True),
            Input("score-attr-scatter", "relayoutData"),
            prevent_initial_call=True,
        )
        def clear_pcp_on_scatter_reset(relayoutData):
            if not isinstance(relayoutData, dict):
                raise PreventUpdate

            # ignore resize noise
            if relayoutData.get("autosize") is True or "width" in relayoutData or "height" in relayoutData:
                raise PreventUpdate

            if relayoutData.get("xaxis.autorange") is True or relayoutData.get("yaxis.autorange") is True:
                return {"constraints": {}}

            if relayoutData.get("selections") == [] or relayoutData.get("selections") is None:
                return {"constraints": {}}

            raise PreventUpdate

        # Scatter figure + highlight selected (and show selected in scatter when clicking map)
        @self.app.callback(
            Output("score-attr-scatter", "figure"),
            Input("filters-applied-store", "data"),
            Input("scatter-y-attr", "value"),
            Input("selected-country-store", "data"),
            Input("pcp-brush-store", "data"),
        )
        def update_score_attr_scatter(filters_applied, y_col, selected_country, pcp_store):
            filters_applied = filters_applied or {}
            y_col = y_col or "Real_GDP_per_Capita_USD"

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

            # apply PCP constraints only (do NOT apply scatter store here)
            if pcp_store and isinstance(pcp_store, dict) and (pcp_store.get("constraints") or {}):
                scored_df = self._apply_intersection(scored_df, {"countries": []}, pcp_store)

            dfp = scored_df[["Country", "RE_Opp", y_col]].copy()
            dfp["RE_Opp"] = self._safe_numeric_series(dfp["RE_Opp"], default=np.nan)
            dfp[y_col] = self._safe_numeric_series(dfp[y_col], default=np.nan)
            dfp = dfp.dropna(subset=["RE_Opp", y_col])
            if dfp.empty:
                return self._empty_message_fig("No data")

            y_scaled = dfp[y_col] / float(meta.get("scale", 1.0) or 1.0)
            y_title = meta["label"] + (f" ({meta['unit']})" if meta.get("unit") else "")

            dfp2 = dfp.assign(_y=y_scaled).reset_index(drop=True)

            fig = px.scatter(
                dfp2,
                x="RE_Opp",
                y="_y",
                hover_name="Country",
                title=f"Score vs {meta['label']}",
                color_discrete_sequence=["#38a89a"],
            )

            fig.update_traces(
                marker=dict(size=7, opacity=0.65),
                selected=dict(marker=dict(opacity=0.95, size=9)),
                unselected=dict(marker=dict(opacity=0.18)),
            )

            fig.update_layout(dragmode="lasso", uirevision="score-attr-scatter")

            # visually + programmatically select country when clicking map
            if selected_country:
                mask = dfp2["Country"].astype(str) == str(selected_country)
                idxs = dfp2.index[mask].tolist()

                # highlight as "selected" in the main trace
                if idxs:
                    fig.update_traces(selectedpoints=idxs)

                    # also add the big marker label so it’s obvious
                    row = dfp2.loc[idxs[0]]
                    fig.add_trace(
                        go.Scatter(
                            x=[float(row["RE_Opp"])],
                            y=[float(row["_y"])],
                            mode="markers+text",
                            text=[str(selected_country)],
                            textposition="top center",
                            marker=dict(size=16, color="#66fcf1", opacity=0.95),
                            hoverinfo="skip",
                            showlegend=False,
                        )
                    )

            fig.update_layout(
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

        # Drilldown: Radar + Values ONLY
        @self.app.callback(
            Output("drilldown-country-title", "children"),
            Output("drilldown-investor-label", "children"),
            Output("drilldown-radar", "figure"),
            Output("drilldown-values", "children"),
            Input("selected-country-store", "data"),
            Input("filters-applied-store", "data"),
        )
        def render_country_drilldown(selected_country, filters_applied):
            try:
                investor_label = self.INVESTOR_LABEL
                filters_applied = filters_applied or {}

                if not selected_country:
                    placeholder_fig = self._empty_message_fig("Click a country on the map.")
                    values_box = [html.Div(style={"color": "#9aa4b2", "fontSize": "12px"}, children="Select a country to see exact values.")]
                    return ("Click a country on the map", investor_label, placeholder_fig, values_box)

                try:
                    scored_df = self._score_mode_b(scoring_df, filters_applied)
                except Exception:
                    scored_df = compute_real_estate_scores(scoring_df, fit_df=scoring_df, keep_intermediate=True)

                score_col = "RE_Opp"
                hit = scored_df[scored_df["Country"].astype(str) == str(selected_country)]
                if hit.empty:
                    msg = f"Country not found: {selected_country}"
                    placeholder_fig = self._empty_message_fig(msg)
                    values_box = [html.Div(style={"color": "#9aa4b2", "fontSize": "12px"}, children=msg)]
                    return msg, investor_label, placeholder_fig, values_box

                df_sub = self._subset_nearest(scored_df, str(selected_country), score_col, n=60).copy()

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

                df_sel = df_sub[df_sub["Country"].astype(str) == str(selected_country)].head(1)
                if df_sel.empty:
                    radar_fig = self._empty_message_fig("No data for selected country.")
                else:
                    sel_vals = [float(df_sel.iloc[0][lab]) for lab in labels]
                    med_vals = [float(np.nanmedian(self._safe_numeric_series(df_sub[lab], np.nan))) for lab in labels]

                    theta = labels + [labels[0]]
                    r_sel = sel_vals + [sel_vals[0]]
                    r_med = med_vals + [med_vals[0]]

                    radar_fig = go.Figure()
                    radar_fig.add_trace(go.Scatterpolar(r=r_med, theta=theta, fill="toself", name="Cohort median", opacity=0.25))
                    radar_fig.add_trace(go.Scatterpolar(r=r_sel, theta=theta, fill="toself", name=str(selected_country), opacity=0.80))
                    radar_fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Inter, sans-serif", color="white"),
                        margin=dict(l=20, r=20, t=10, b=10),
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0, font=dict(size=11)),
                        polar=dict(
                            bgcolor="rgba(0,0,0,0)",
                            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(color="rgba(255,255,255,0.7)", size=10),
                                            gridcolor="rgba(255,255,255,0.10)"),
                            angularaxis=dict(tickfont=dict(color="rgba(255,255,255,0.85)", size=11),
                                             gridcolor="rgba(255,255,255,0.10)"),
                        ),
                    )

                sel_row = hit.iloc[0]

                def _row(lbl, val):
                    return html.Div(
                        style={"display": "flex", "justifyContent": "space-between", "gap": "12px", "padding": "6px 0px",
                               "borderBottom": "1px solid rgba(255,255,255,0.06)"},
                        children=[
                            html.Span(lbl, style={"color": "#9aa4b2", "fontSize": "12px"}),
                            html.Span(val, style={"color": "white", "fontSize": "12px", "fontWeight": 600}),
                        ],
                    )

                values_rows = [
                    html.Div(
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "8px"},
                        children=[
                            html.Span("EXACT VALUES", style={"color": "#9aa4b2", "fontSize": "11px", "letterSpacing": "0.14em"}),
                            html.Span(f"Score: {float(sel_row.get('RE_Opp', 0.0)):.1f}/100",
                                      style={"color": "white", "fontSize": "12px", "fontWeight": 700}),
                        ],
                    )
                ]
                values_rows.extend([
                    _row("GDP per Capita (USD)", self._fmt_raw_value("Real_GDP_per_Capita_USD", sel_row.get("Real_GDP_per_Capita_USD"))),
                    _row("Population", self._fmt_raw_value("Total_Population", sel_row.get("Total_Population"))),
                    _row("Population Growth (%)", self._fmt_raw_value("Population_Growth_Rate", sel_row.get("Population_Growth_Rate"))),
                    _row("Net Migration Rate", self._fmt_raw_value("Net_Migration_Rate", sel_row.get("Net_Migration_Rate"))),
                    _row("Unemployment (%)", self._fmt_raw_value("Unemployment_Rate_percent", sel_row.get("Unemployment_Rate_percent"))),
                    _row("Public Debt (% of GDP)", self._fmt_raw_value("Public_Debt_percent_of_GDP", sel_row.get("Public_Debt_percent_of_GDP"))),
                ])

                return title, investor_label, radar_fig, values_rows

            except Exception as e:
                msg = f"Drilldown error: {type(e).__name__}: {e}"
                investor_label = self.INVESTOR_LABEL
                placeholder_fig = self._empty_message_fig(msg)
                values_box = [html.Div(style={"color": "#9aa4b2", "fontSize": "12px"}, children=msg)]
                return msg, investor_label, placeholder_fig, values_box

        # PCP figure + cohort store
        @self.app.callback(
            Output("drilldown-pcp", "figure"),
            Output("drilldown-cohort-store", "data"),
            Input("selected-country-store", "data"),
            Input("filters-applied-store", "data"),
            Input("scatter-brush-store", "data"),
            Input("pcp-brush-store", "data"),
        )
        def update_pcp_and_cohort(selected_country, filters_applied, scatter_store, pcp_store):
            filters_applied = filters_applied or {}

            if not selected_country:
                return self._empty_message_fig("Click a country on the map to show PCP."), None

            try:
                scored_df = self._score_mode_b(scoring_df, filters_applied)
            except Exception:
                scored_df = compute_real_estate_scores(scoring_df, fit_df=scoring_df, keep_intermediate=True)

            score_col = "RE_Opp"
            hit = scored_df[scored_df["Country"].astype(str) == str(selected_country)]
            if hit.empty:
                msg = f"Country not found: {selected_country}"
                return self._empty_message_fig(msg), None

            scatter_countries = []
            if scatter_store and isinstance(scatter_store, dict):
                scatter_countries = scatter_store.get("countries", []) or []
            if scatter_countries:
                cohort_df = scored_df[scored_df["Country"].astype(str).isin([str(c) for c in scatter_countries])].copy()
                if str(selected_country) not in cohort_df["Country"].astype(str).values:
                    cohort_df = pd.concat([hit, cohort_df], ignore_index=True).drop_duplicates(subset=["Country"])
            else:
                cohort_df = scored_df.copy()

            cohort_df[score_col] = self._safe_numeric_series(cohort_df.get(score_col, 0.0), default=0.0).clip(0, 100)
            cohort_df = cohort_df.sort_values(score_col, ascending=False)
            top = cohort_df.head(35)
            bottom = cohort_df.tail(15)
            sel = cohort_df[cohort_df["Country"].astype(str) == str(selected_country)]
            pcp_df = pd.concat([top, bottom, sel], ignore_index=True).drop_duplicates(subset=["Country"])

            
            raw_cols = [
                ("Real_GDP_per_Capita_USD", "GDP/cap", False),
                ("Total_Population", "Pop", False),
                ("Population_Growth_Rate", "Pop Growth", False),
                ("Net_Migration_Rate", "Migration", False),
                ("Unemployment_Rate_percent", "Unemp", True),
                ("Public_Debt_percent_of_GDP", "Debt", True),
            ]
            AXIS_LABEL = {
                "GDP/cap": "Real GDP per Capita (USD)",
                "Pop": "Total Population",
                "Pop Growth": "Population Growth Rate (%)",
                "Migration": "Net Migration Rate",
                "Unemp": "Unemployment Rate (%)",
                "Debt": "Public Debt (% of GDP)",
            }

            labels =[]
            for col, lab, inv in raw_cols:
                if col not in pcp_df.columns:
                    pcp_df[col] = np.nan
                pcp_df[lab] = self._normalize_0_100(pcp_df, col, invert=inv)
                labels.append(lab)

            constraints = {}
            if pcp_store and isinstance(pcp_store, dict):
                constraints = pcp_store.get("constraints", {}) or {}
            AXIS_LABEL = {
                "GDP/cap": "Real GDP per Capita (USD)",
                "Pop": "Total Population",
                "Pop Growth": "Population Growth Rate (%)",
                "Migration": "Net Migration Rate",
                "Unemp": "Unemployment Rate (%)",
                "Debt": "Public Debt (% of GDP)",
            }

            dims = []
            for lab in labels:
                d = dict(
                     label=AXIS_LABEL.get(lab, lab),
                     range=[0, 100], 
                     values=self._safe_numeric_series(pcp_df[lab], 0.0).values,
                     tickvals = [0 ,20 , 40, 60 , 80, 100],
                     ticktext = ["0" , "20", "40", "60", "80","100"],
                     )
                if lab in constraints:
                    d["constraintrange"] = constraints[lab]
                dims.append(d)

            pcp_fig = go.Figure()
            pcp_fig.add_trace(
                go.Parcoords(
                    line=dict(
                        color=self._safe_numeric_series(pcp_df[score_col], 0.0).values,
                        colorscale=DIM_GREEN_SCALE,
                        cmin=float(pcp_df[score_col].min()),
                        cmax=float(pcp_df[score_col].max()),
                        showscale=True,
                    ),
                    dimensions=dims,
                    labelfont=dict(color="white", size=12),
                    tickfont=dict(color="rgba(255,255,255,0.7)", size=10),
                )
            )
            pcp_fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", color="white"),
                margin=dict(l=90, r=60, t=90, b=30),
                
            
            )
            


            cohort_payload = {
                "selected_country": str(selected_country),
                "score_col": "RE_Opp",
                "labels": labels,
                "records": pcp_df[
                    ["Country", "RE_Opp"] + labels + [
                        "Real_GDP_per_Capita_USD",
                        "Total_Population",
                        "Population_Growth_Rate",
                        "Net_Migration_Rate",
                        "Unemployment_Rate_percent",
                        "Public_Debt_percent_of_GDP",
                    ]
                ].to_dict("records"),
            }

            return pcp_fig, cohort_payload

        # Store PCP brushing constraints
        @self.app.callback(
            Output("pcp-brush-store", "data", allow_duplicate=True),
            Input("drilldown-pcp", "restyleData"),
            State("drilldown-cohort-store", "data"),
            State("pcp-brush-store", "data"),
            prevent_initial_call=True,
        )
        def store_pcp_brush(restyleData, cohort_store, current_store):
            if not cohort_store or "records" not in cohort_store:
                raise PreventUpdate

            current_constraints = {}
            if isinstance(current_store, dict):
                current_constraints = current_store.get("constraints", {}) or {}

            if not restyleData:
                raise PreventUpdate

            patch = {}
            if isinstance(restyleData, (list, tuple)) and len(restyleData) >= 1 and isinstance(restyleData[0], dict):
                patch = restyleData[0]
            elif isinstance(restyleData, dict):
                patch = restyleData

            labels = cohort_store.get("labels", [])
            if not labels:
                raise PreventUpdate

            updated = dict(current_constraints)
            saw_any = False

            for k, v in patch.items():
                k = str(k)
                if "constraintrange" not in k:
                    continue
                saw_any = True
                try:
                    idx = int(k.split("dimensions[")[1].split("]")[0])
                except Exception:
                    continue
                if idx < 0 or idx >= len(labels):
                    continue
                axis_label = labels[idx]

                if v is None:
                    updated.pop(axis_label, None)
                else:
                    updated[axis_label] = v

            if not saw_any:
                raise PreventUpdate

            return {"constraints": updated}

        # PCP brushing -> update RADAR + VALUES ONLY
        @self.app.callback(
            Output("drilldown-radar", "figure", allow_duplicate=True),
            Output("drilldown-values", "children", allow_duplicate=True),
            Input("pcp-brush-store", "data"),
            State("drilldown-cohort-store", "data"),
            prevent_initial_call=True,
        )
        def apply_pcp_brush_to_panels(brush_store, cohort_store):
            if not cohort_store or "records" not in cohort_store:
                raise PreventUpdate

            constraints = (brush_store or {}).get("constraints", {}) if brush_store else {}
            df = pd.DataFrame(cohort_store["records"])
            labels = list(cohort_store.get("labels", []))
            selected_country = str(cohort_store.get("selected_country", ""))

            brushed_df = self._apply_constraints(df, constraints)
            cohort_for_median = brushed_df if constraints else df

            sel_hit = df[df["Country"].astype(str) == selected_country].head(1)
            if sel_hit.empty or not labels:
                radar_fig = self._empty_message_fig("No data.")
            else:
                sel_vals = [float(sel_hit.iloc[0][lab]) for lab in labels]
                med_vals = [float(np.nanmedian(self._safe_numeric_series(cohort_for_median[lab], np.nan))) for lab in labels]
                theta = labels + [labels[0]]
                r_sel = sel_vals + [sel_vals[0]]
                r_med = med_vals + [med_vals[0]]

                radar_fig = go.Figure()
                radar_fig.add_trace(go.Scatterpolar(r=r_med, theta=theta, fill="toself",
                                                    name=("Brushed median" if constraints else "Cohort median"), opacity=0.25))
                radar_fig.add_trace(go.Scatterpolar(r=r_sel, theta=theta, fill="toself",
                                                    name=str(selected_country), opacity=0.80))
                radar_fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter, sans-serif", color="white"),
                    margin=dict(l=20, r=20, t=10, b=10),
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0, font=dict(size=11)),
                    polar=dict(
                        bgcolor="rgba(0,0,0,0)",
                        radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(color="rgba(255,255,255,0.7)", size=10),
                                        gridcolor="rgba(255,255,255,0.10)"),
                        angularaxis=dict(tickfont=dict(color="rgba(255,255,255,0.85)", size=11),
                                         gridcolor="rgba(255,255,255,0.10)"),
                    ),
                )

            def _row(lbl, val):
                return html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "gap": "12px", "padding": "6px 0px",
                           "borderBottom": "1px solid rgba(255,255,255,0.06)"},
                    children=[
                        html.Span(lbl, style={"color": "#9aa4b2", "fontSize": "12px"}),
                        html.Span(val, style={"color": "white", "fontSize": "12px", "fontWeight": 600}),
                    ],
                )

            if sel_hit.empty:
                return radar_fig, [html.Div(style={"color": "#9aa4b2", "fontSize": "12px"}, children="No selected country row.")]

            sel_row = sel_hit.iloc[0]
            score = float(sel_row.get("RE_Opp", 0.0))

            values_rows = [
                html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "8px"},
                    children=[
                        html.Span("EXACT VALUES", style={"color": "#9aa4b2", "fontSize": "11px", "letterSpacing": "0.14em"}),
                        html.Span(f"Score: {score:.1f}/100", style={"color": "white", "fontSize": "12px", "fontWeight": 700}),
                    ],
                )
            ]
            values_rows.extend([
                _row("GDP per Capita (USD)", self._fmt_raw_value("Real_GDP_per_Capita_USD", sel_row.get("Real_GDP_per_Capita_USD"))),
                _row("Population", self._fmt_raw_value("Total_Population", sel_row.get("Total_Population"))),
                _row("Population Growth (%)", self._fmt_raw_value("Population_Growth_Rate", sel_row.get("Population_Growth_Rate"))),
                _row("Net Migration Rate", self._fmt_raw_value("Net_Migration_Rate", sel_row.get("Net_Migration_Rate"))),
                _row("Unemployment (%)", self._fmt_raw_value("Unemployment_Rate_percent", sel_row.get("Unemployment_Rate_percent"))),
                _row("Public Debt (% of GDP)", self._fmt_raw_value("Public_Debt_percent_of_GDP", sel_row.get("Public_Debt_percent_of_GDP"))),
            ])

            return radar_fig, values_rows

    # ---------- Layout ----------
    def setup_layout(self):
        return html.Div(
            className="app-container",
            children=[
                dcc.Store(id="sidebar-state", data={"collapsed": False}),
                dcc.Store(id="plotly-resize-signal", data=0),

                dcc.Store(id="selected-country-store", storage_type="memory"),
                dcc.Store(id="filters-applied-store", storage_type="memory"),

                dcc.Store(id="drilldown-cohort-store", storage_type="memory"),
                dcc.Store(id="pcp-brush-store", storage_type="memory"),
                dcc.Store(id="scatter-brush-store", storage_type="memory"),
                dcc.Store(id="world-map-view-store", storage_type="memory"),

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


