from dash import Dash, Input, Output, State, html, ctx, ALL, dcc
from dash.exceptions import PreventUpdate

from UI_Components.Sidebar import Sidebar
from UI_Components.MapView import MapView
from UI_Components.AnalyticsPanel import AnalyticsPanel

from scoring import load_and_process_data
from UTILS.weighted_scoring import (
    compute_weighted_score,
    PERSONA_FEATURES,
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


class Main:
    def __init__(self):
        self.app = Dash(__name__, suppress_callback_exceptions=True)
        self.app.title = "NEXUS SCOUT"

        self.sidebar = Sidebar()
        self.map_view = MapView()
        self.analytics_panel = AnalyticsPanel()

        self.PERSONAS = getattr(self.sidebar, "PERSONAS", {"real_estate": {"name": "REAL ESTATE"}})
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

    def _default_weights_for_persona(self, persona: str) -> dict:
        feats = PERSONA_FEATURES.get(persona, [])
        return {str(f["col"]): 3 for f in feats}

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
            prevent_initial_call=False,
        )
        def render_filter_range_labels(values_list):
            # If the sidebar sliders are not mounted yet, Dash will pass an empty list.
            if not values_list:
                return []

            labels = []
            for v in values_list:
                # RangeSlider value should be [min, max]
                if isinstance(v, (list, tuple)) and len(v) == 2:
                    lo, hi = v
                    # Prefer compact formatting (ints if possible)
                    try:
                        lo_f = float(lo)
                        hi_f = float(hi)
                        if lo_f.is_integer() and hi_f.is_integer():
                            labels.append(f"{int(lo_f)}–{int(hi_f)}")
                        else:
                            labels.append(f"{lo_f:.2f}–{hi_f:.2f}")
                    except Exception:
                        labels.append(f"{lo}–{hi}")
                else:
                    # Fallback (unexpected shape)
                    labels.append(str(v))

            return labels

        # -----------------------------
        # Map updates
        # -----------------------------
        @self.app.callback(
            Output("world-map", "figure"),
            Input("selected-persona-store", "data"),
        )
        def update_map_on_persona(persona):
            persona = persona or "real_estate"
            weights = self._default_weights_for_persona(persona)

            try:
                result = compute_weighted_score(scoring_df, persona, weights)
            except Exception:
                return self._empty_world_figure()

            scored_df = result.scored_df
            score_col = result.score_col

            df_plot = scored_df[["Country", score_col]].dropna()
            if df_plot.empty:
                return self._empty_world_figure()

            fig = px.choropleth(
                df_plot,
                locations="Country",
                locationmode="country names",
                color=score_col,
                hover_name="Country",
                title=f"<b>{self.PERSONAS[persona]['name']}</b>",
                color_continuous_scale=GREEN_SCALE,
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
                coloraxis=dict(
                    cmin=float(df_plot[score_col].min()),
                    cmax=float(df_plot[score_col].max()),
                ),
            )
            return fig

        # -----------------------------
        # Top 5
        # -----------------------------
        @self.app.callback(
            Output("top-5-chart", "children"),
            Input("selected-persona-store", "data"),
        )
        def top5(persona):
            persona = persona or "real_estate"
            weights = self._default_weights_for_persona(persona)

            try:
                result = compute_weighted_score(scoring_df, persona, weights)
            except Exception:
                return "No data"

            scored_df = result.scored_df
            score_col = result.score_col

            df_top = scored_df[["Country", score_col]].dropna().nlargest(5, score_col)
            if df_top.empty:
                return "No data"

            bar_fig = px.bar(
                df_top,
                x="Country",
                y=score_col,
                title=f"Top 5 — {self.PERSONAS[persona]['name']}",
                color_discrete_sequence=["#1f5c52"],
            )
            bar_fig = self._dark_fig_layout(bar_fig)
            return dcc.Graph(figure=bar_fig, config={"displayModeBar": False})

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
            Input("selected-persona-store", "data"),
        )
        def render_country_drilldown(selected_country, persona):
            try:
                persona = persona or "real_estate"
                investor_label = self.PERSONAS.get(persona, {"name": persona}).get("name", persona)

                if not selected_country:
                    return (
                        "Click a country on the map",
                        investor_label,
                        self._empty_message_fig("Click a country to show SPLOM."),
                        self._empty_message_fig("Click a country to show PCP."),
                    )

                weights = self._default_weights_for_persona(persona)

                result = compute_weighted_score(scoring_df, persona, weights)
                scored_df = result.scored_df
                score_col = result.score_col

                hit = scored_df[scored_df["Country"].astype(str) == str(selected_country)]
                if hit.empty:
                    msg = f"Country not found: {selected_country}"
                    return msg, investor_label, self._empty_message_fig(msg), self._empty_message_fig(msg)

                # Comparison set
                df_sub = self._subset_nearest(scored_df, str(selected_country), score_col, n=60).copy()

                # Persona feature defs
                defs = PERSONA_FEATURES.get(persona, [])
                norm_cols = [f"dyn_norm__{d['col']}" for d in defs]

                # Long labels -> short labels
                long_labels = [str(d.get("label", d["col"])) for d in defs]
                labels = [SHORT_LABELS.get(l, l) for l in long_labels]

                # Ensure norm columns exist and build display columns (0..100)
                for c in norm_cols:
                    if c not in df_sub.columns:
                        df_sub[c] = 0.0

                for c, lab in zip(norm_cols, labels):
                    df_sub[lab] = (
                        self._safe_numeric_series(df_sub[c], default=0.0)
                        .clip(0, 1)
                        * 100.0
                    )

                # Make sure score_col is numeric for coloring
                df_sub[score_col] = self._safe_numeric_series(df_sub[score_col], default=0.0)

                # Header title (shown in your H3)
                title = f"{selected_country} — {investor_label} | Compare: {len(df_sub)}"

                # ---------- SPLOM (clean) ----------
                splom_fig = px.scatter_matrix(
                    df_sub,
                    dimensions=labels,
                    color=score_col,
                    hover_name="Country",
                    color_continuous_scale=GREEN_SCALE,
                )

                # Cleaner matrix
                splom_fig.update_traces(
                    diagonal_visible=False,
                    showupperhalf=False,
                    showlowerhalf=True,
                    marker=dict(size=5, opacity=0.55),
                )

                # Highlight selected strongly
                sel_mask = df_sub["Country"].astype(str).values == str(selected_country)
                if len(splom_fig.data) > 0:
                    sizes = np.where(sel_mask, 12, 5)
                    splom_fig.data[0].update(marker=dict(size=sizes, opacity=0.65))

                splom_fig.update_layout(
                    title=None,  # avoid duplicate title inside plot
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter, sans-serif", color="white", size=11),
                    margin=dict(l=10, r=10, t=10, b=10),
                    coloraxis_showscale=False,  # keep only PCP colorbar
                )
                splom_fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.06)")
                splom_fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.06)")

                # ---------- PCP (reduce spaghetti) ----------
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

                # Background lines (reduced set)
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

                # Selected overlay (strong cyan)
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
                    title=None,  # avoid duplicate title
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter, sans-serif", color="white"),
                    margin=dict(l=10, r=10, t=10, b=10),
                )

                return title, investor_label, splom_fig, pcp_fig

            except Exception as e:
                msg = f"Drilldown error: {type(e).__name__}: {e}"
                persona = persona or "real_estate"
                investor_label = self.PERSONAS.get(persona, {"name": persona}).get("name", persona)
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
                dcc.Store(id="selected-persona-store", data="real_estate", storage_type="memory"),

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

