from dash import Dash, Input, Output, State, html, ctx, ALL, dcc
from dash.exceptions import PreventUpdate

from UI_Components.Sidebar import Sidebar
from UI_Components.MapView import MapView
from UI_Components.AnalyticsPanel import AnalyticsPanel

from scoring import load_and_process_data
from UTILS.helpers_breakdown import build_breakdown

from plotly import express as px
from plotly import graph_objects as go

import pandas as pd
import numpy as np


# -----------------------------
# Data
# -----------------------------
scoring_df = load_and_process_data()





# -----------------------------
# App
# -----------------------------
class Main:
    def __init__(self):
        self.app = Dash(__name__)
        self.app.title = "NEXUS SCOUT"

        self.sidebar = Sidebar()
        self.map_view = MapView()
        self.analytics_panel = AnalyticsPanel()

        self.PERSONA_TO_SCORE = {
            "real_estate": "RE_Opp",
            "agriculture": "Ag_Opp",
            "logistics": "Logistics_Opp",
            "telecom": "Telecom_Opp",
            "fintech": "Fintech_Opp",
            "retail": "Retail_Opp",
        }

        # Use the same personas dict as Sidebar
        self.PERSONAS = self.sidebar.PERSONAS

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
        """
        Applies consistent dark/transparent styling to any chart so you don't get white boxes.
        """
        if title:
            fig.update_layout(title=title)

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="white"),
            margin=dict(l=10, r=10, t=60, b=10),
        )
        # Make axis text white (for non-geo charts)
        fig.update_xaxes(color="white", gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.12)")
        fig.update_yaxes(color="white", gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.12)")
        return fig

    # ---------- Callbacks ----------
    def register_callbacks(self):

        # -----------------------------
        # Sidebar state: collapse + active panel
        # -----------------------------
        @self.app.callback(
            Output("sidebar-state", "data"),
            Input("sidebar-collapse-btn", "n_clicks"),
            Input({"type": "sidebar-nav", "index": ALL}, "n_clicks"),
            State("sidebar-state", "data"),
            prevent_initial_call=True,
        )
        def update_sidebar_state(collapse_clicks, nav_clicks, state):
            if state is None:
                state = {"collapsed": False, "active": "investors"}

            trigger = ctx.triggered_id
            if trigger is None:
                raise PreventUpdate

            if trigger == "sidebar-collapse-btn":
                state["collapsed"] = not state.get("collapsed", False)
                return state

            if isinstance(trigger, dict) and trigger.get("type") == "sidebar-nav":
                state["active"] = trigger.get("index")
                if state.get("collapsed", False):
                    state["collapsed"] = False
                return state

            raise PreventUpdate

        @self.app.callback(
            Output("sidebar-wrapper", "className"),
            Output({"type": "sidebar-nav", "index": "investors"}, "className"),
            Output({"type": "sidebar-nav", "index": "geo"}, "className"),
            Output({"type": "sidebar-nav", "index": "bookmarks"}, "className"),
            Output("sidebar-panel-investors", "className"),
            Output("sidebar-panel-geo", "className"),
            Output("sidebar-panel-bookmarks", "className"),
            Output("map-and-analytics-container", "className"),
            Input("sidebar-state", "data"),
        )
        def apply_sidebar_classes(state):
            if not state:
                state = {"collapsed": False, "active": "investors"}

            collapsed = state.get("collapsed", False)
            active = state.get("active", "investors")

            sidebar_class = "sidebar sidebar--collapsed" if collapsed else "sidebar"
            content_class = (
                "map-and-analytics-container map-and-analytics-container--collapsed"
                if collapsed else
                "map-and-analytics-container"
            )

            def panel_class(key):
                base = "sidebar-panel"
                return f"{base} sidebar-panel--active" if active == key else base

            def nav_class(key):
                base = "sidebar-nav-item"
                return f"{base} sidebar-nav-item--active" if active == key else base

            return (
                sidebar_class,
                nav_class("investors"),
                nav_class("geo"),
                nav_class("bookmarks"),
                panel_class("investors"),
                panel_class("geo"),
                panel_class("bookmarks"),
                content_class,
            )

        # -----------------------------
        # Persona selection (SIDEBAR is the ONLY source of truth)
        # -----------------------------
        @self.app.callback(
            Output("selected-persona-store", "data"),
            Input({"type": "persona-card", "index": ALL}, "n_clicks"),
            State("selected-persona-store", "data"),
            prevent_initial_call=True,
        )
        def set_persona_from_sidebar(_clicks, current_persona):
            trigger = ctx.triggered_id
            if isinstance(trigger, dict) and trigger.get("type") == "persona-card":
                return trigger.get("index", "real_estate")
            return current_persona or "real_estate"

        # -----------------------------
        # Map updates based on persona store
        # -----------------------------
        @self.app.callback(
            Output("world-map", "figure"),
            Input("selected-persona-store", "data"),
        )
        def update_map_on_persona(persona):
            persona = persona or "real_estate"
            score_col = self.PERSONA_TO_SCORE.get(persona)

            if not score_col or score_col not in scoring_df.columns:
                return self._empty_world_figure()

            df_plot = scoring_df[["Country", score_col]].dropna()
            if df_plot.empty:
                return self._empty_world_figure()

            fig = px.choropleth(
                df_plot,
                locations="Country",
                locationmode="country names",
                color=score_col,
                hover_name="Country",
                title=f"<b>{self.PERSONAS[persona]['name']}</b>",
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
        # Top 5 uses persona store
        # -----------------------------
        @self.app.callback(
            Output("top-5-chart", "children"),
            Input("selected-persona-store", "data"),
        )
        def top5(persona):
            persona = persona or "real_estate"
            score_col = self.PERSONA_TO_SCORE.get(persona)

            if not score_col or score_col not in scoring_df.columns:
                return "No data"

            df_top = scoring_df[["Country", score_col]].dropna().nlargest(5, score_col)
            bar_fig = px.bar(
                df_top,
                x="Country",
                y=score_col,
                title=f"Top 5 — {self.PERSONAS[persona]['name']}",
            )
            bar_fig = self._dark_fig_layout(bar_fig)

            # Neural map scatter
            if "PCA_1" in scoring_df.columns and "PCA_2" in scoring_df.columns:
                df_scatter = scoring_df[["Country", score_col, "PCA_1", "PCA_2"]].dropna(subset=["PCA_1", "PCA_2", score_col])
                scatter_fig = px.scatter(
                    df_scatter,
                    x="PCA_1",
                    y="PCA_2",
                    color=score_col,
                    hover_name="Country",
                    title=f"Neural Country Map — {self.PERSONAS[persona]['name']}",
                )
                scatter_fig = self._dark_fig_layout(scatter_fig)

                return html.Div([
                    dcc.Graph(figure=bar_fig, config={"displayModeBar": False}),
                    dcc.Graph(figure=scatter_fig, config={"displayModeBar": False}),
                ])

            return dcc.Graph(figure=bar_fig, config={"displayModeBar": False})

        # -----------------------------
        # Country click -> store selected country
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

            # Choropleth commonly uses "location" for the clicked region
            if p.get("location"):
                return str(p["location"])

            # Fallback
            if p.get("text"):
                return str(p["text"])

            raise PreventUpdate

        # -----------------------------
        # Drilldown: selected country + selected persona -> waterfall + table
        # -----------------------------
        @self.app.callback(
            Output("drilldown-country-title", "children"),
            Output("drilldown-breakdown-chart", "figure"),
            Output("drilldown-breakdown-table", "children"),
            Input("selected-country-store", "data"),
            Input("selected-persona-store", "data"),
        )
        def render_country_drilldown(selected_country, persona):
            persona = persona or "real_estate"

            if not selected_country:
                fig = go.Figure()
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"),
                    xaxis=dict(visible=False),
                    yaxis=dict(visible=False),
                    margin=dict(l=10, r=10, t=10, b=10),
                    annotations=[dict(
                        text="Click a country on the map.",
                        showarrow=False,
                        x=0.5, y=0.5,
                        font=dict(color="white")
                    )],
                )
                return "No country selected", fig, ""

            hit = scoring_df[scoring_df["Country"].astype(str) == str(selected_country)]
            if hit.empty:
                fig = go.Figure()
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"),
                    xaxis=dict(visible=False),
                    yaxis=dict(visible=False),
                    margin=dict(l=10, r=10, t=10, b=10),
                    annotations=[dict(
                        text=f"Country not found: {selected_country}",
                        showarrow=False,
                        x=0.5, y=0.5,
                        font=dict(color="white")
                    )],
                )
                return f"Country not found: {selected_country}", fig, ""

            row = hit.iloc[0]
            breakdown, final_score = build_breakdown(scoring_df, row, persona)

            # Waterfall chart (transparent/dark)
            x = [r["factor"] for r in breakdown] + ["Final"]
            y = [r["contribution"] for r in breakdown] + [final_score]
            measure = ["relative"] * len(breakdown) + ["total"]

            fig = go.Figure(go.Waterfall(x=x, y=y, measure=measure))
            fig.update_layout(
                title=f"{row['Country']} — {self.PERSONAS.get(persona, {'name': persona})['name']} Score: {final_score:.2f}",
                title_font=dict(family="Inter, sans-serif", size=18, color="white"),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", color="white"),
                margin=dict(l=10, r=10, t=50, b=10),
                yaxis=dict(title="Points"),
            )
            fig.update_xaxes(color="white")
            fig.update_yaxes(color="white", gridcolor="rgba(255,255,255,0.08)")

            # Table (white text, transparent background)
            header = html.Tr([
                html.Th("Factor"),
                html.Th("Value Used"),
                html.Th("Weight"),
                html.Th("Contribution"),
            ])

            body = []
            for r in breakdown:
                body.append(html.Tr([
                    html.Td(r["factor"]),
                    html.Td(f"{r['value_used']:.2f}"),
                    html.Td(f"{r['weight']:.2f}"),
                    html.Td(f"{r['contribution']:.2f}"),
                ]))

            body.append(html.Tr([
                html.Td(html.B("Final Score")),
                html.Td(""),
                html.Td(""),
                html.Td(html.B(f"{final_score:.2f}")),
            ]))

            table = html.Table(
                [html.Thead(header), html.Tbody(body)],
                style={
                    "width": "100%",
                    "color": "white",
                    "fontSize": "12px",
                    "borderCollapse": "collapse",
                    "backgroundColor": "rgba(0,0,0,0)",
                },
            )

            title = f"{row['Country']} — Composite Score: {final_score:.2f}"
            return title, fig, table

    # ---------- Layout ----------
    def setup_layout(self):
        return html.Div(
            className="app-container",
            children=[
                dcc.Store(id="sidebar-state", data={"collapsed": False, "active": "investors"}),
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
