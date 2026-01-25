from dash import Dash, Input, Output, State, html, ctx, ALL, dcc, no_update
from dash.exceptions import PreventUpdate

from UI_Components.Sidebar import Sidebar
from UI_Components.MapView import MapView
from UI_Components.AnalyticsPanel import AnalyticsPanel

from scoring import load_and_process_data
from UTILS.weighted_scoring import compute_weighted_score, build_score_breakdown_for_country, PERSONA_FEATURES

from plotly import express as px
from plotly import graph_objects as go



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



# -----------------------------
# App
# -----------------------------
class Main:
    def __init__(self):
        self.app = Dash(__name__, suppress_callback_exceptions=True)
        self.app.title = "NEXUS SCOUT"

        self.sidebar = Sidebar()
        self.map_view = MapView()
        self.analytics_panel = AnalyticsPanel()



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

    def _default_weights_for_persona(self, persona: str) -> dict:
        """Default importance weights (1-5) for each of the 6 attributes of the persona."""
        feats = PERSONA_FEATURES.get(persona, [])
        return {f["col"]: 3 for f in feats}

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

            trigger = ctx.triggered_id
            if trigger is None:
                raise PreventUpdate

            if trigger == "sidebar-collapse-btn":
                state["collapsed"] = not state.get("collapsed", False)
                return state

            raise PreventUpdate

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
                if collapsed else
                "map-and-analytics-container"
            )

            return sidebar_class, content_class

        # -----------------------------
        # Persona selection (SIDEBAR dropdown is the source of truth)
        # -----------------------------
        @self.app.callback(
            Output("selected-persona-store", "data"),
            Input("persona-dropdown", "value"),
            State("selected-persona-store", "data"),
        )
        def set_persona_from_dropdown(value, current_persona):
            # When dropdown exists, it drives the persona selection
            if value:
                return value
            return current_persona or "real_estate"

        # -----------------------------
        # Persona sliders (draft + apply)
        # -----------------------------
        @self.app.callback(
            Output("weights-sliders-container", "children"),
            Output("weights-draft-store", "data", allow_duplicate=True),
            Output("weights-applied-store", "data", allow_duplicate=True),
            Input("selected-persona-store", "data"),
            prevent_initial_call="initial_duplicate",
        )
        def render_persona_sliders(persona):
            persona = persona or "real_estate"
            feats = PERSONA_FEATURES.get(persona, [])

            # Default all to 3
            defaults = {str(f["col"]): 3 for f in feats}

            slider_nodes = []
            for f in feats:
                col = str(f["col"])
                label = str(f.get("label", col))

                slider_nodes.append(
                    html.Div(
                        className="weight-slider",
                        children=[
                            html.Div(
                                className="weight-slider-header",
                                children=[
                                    html.Span(
                                        label,
                                        className="weight-slider-label",
                                    ),
                                    html.Span(
                                        id={"type": "weight-value", "col": col},
                                        className="weight-slider-value",
                                    ),
                                ],
                            ),
                            dcc.Slider(
                                id={"type": "weight-slider", "col": col},
                                min=1,
                                max=5,
                                step=1,
                                value=3,
                                marks={1: "1", 2: "2", 3: "3", 4: "4", 5: "5"},
                                tooltip={"placement": "bottom", "always_visible": False},
                                className="weight-slider-control",
                            ),
                        ],
                    )
                )

            # Initialize both draft and applied to defaults whenever persona changes
            return slider_nodes, defaults, defaults


        @self.app.callback(
            Output("weights-draft-store", "data"),
            Output({"type": "weight-value", "col": ALL}, "children"),
            Input({"type": "weight-slider", "col": ALL}, "value"),
            State({"type": "weight-slider", "col": ALL}, "id"),
            State("weights-draft-store", "data"),
            prevent_initial_call=True,
        )
        def update_draft_weights(values, ids, current):
            # Build a dict {col: value} from the pattern-matching IDs
            current = current or {}
            if not values or not ids:
                raise PreventUpdate
            new_weights = dict(current)

            display_vals = []
            for v, i in zip(values, ids):
                col = str(i.get("col"))
                new_weights[col] = int(v) if v is not None else 3
                display_vals.append(str(new_weights[col]))

            return new_weights, display_vals


        @self.app.callback(
            Output("weights-applied-store", "data", allow_duplicate=True),
            Input("apply-weights-btn", "n_clicks"),
            State("weights-draft-store", "data"),
            prevent_initial_call=True,
        )
        def apply_weights(n_clicks, draft):
            if not n_clicks:
                raise PreventUpdate
            return draft or {}

        # -----------------------------
        # Map updates based on persona store + applied weights
        # -----------------------------
        @self.app.callback(
            Output("world-map", "figure"),
            Input("selected-persona-store", "data"),
            Input("weights-applied-store", "data"),
        )
        def update_map_on_persona(persona, applied_weights):
            persona = persona or "real_estate"
            weights = applied_weights or self._default_weights_for_persona(persona)
            try:
                result = compute_weighted_score(scoring_df, persona, weights)
            except Exception:
                return self._empty_world_figure()
            scored_df = result.scored_df
            score_col = result.score_col  # "dyn_score"

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
                    cmin=df_plot[score_col].min(),
                    cmax=df_plot[score_col].max(),
                )
            )

            return fig

        # -----------------------------
        # Top 5 uses persona store + applied weights
        # -----------------------------
        @self.app.callback(
            Output("top-5-chart", "children"),
            Input("selected-persona-store", "data"),
            Input("weights-applied-store", "data"),
        )
        def top5(persona, applied_weights):
            persona = persona or "real_estate"
            weights = applied_weights or self._default_weights_for_persona(persona)
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
                color_discrete_sequence=["#1a5a52"],
            )
            bar_fig = self._dark_fig_layout(bar_fig)
            
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
        # Drilldown: selected country + selected persona + applied weights -> waterfall + table
        # -----------------------------
        @self.app.callback(
            Output("drilldown-country-title", "children"),
            Output("drilldown-breakdown-chart", "figure"),
            Output("drilldown-breakdown-table", "children"),
            Input("selected-country-store", "data"),
            Input("selected-persona-store", "data"),
            Input("weights-applied-store", "data"),
        )
        def render_country_drilldown(selected_country, persona, applied_weights):
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
            weights = applied_weights or self._default_weights_for_persona(persona)
            result = compute_weighted_score(scoring_df, persona, weights)
            scored_df = result.scored_df
            score_col = result.score_col

            hit = scored_df[scored_df["Country"].astype(str) == str(selected_country)]
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
            breakdown, final_score = build_score_breakdown_for_country(
                scored_df,
                persona,
                result.weights_used,
                str(selected_country),
            )

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
                html.Th("Normalized Value"),
                html.Th("Weight"),
                html.Th("Contribution"),
            ])

            body = []
            for r in breakdown:
                body.append(
                    html.Tr(
                        [
                            html.Td(r["factor"]),
                            html.Td(f"{float(r.get('normalized_value', 0.0)):.2f}"),
                            html.Td(f"{float(r.get('weight', 0.0)):.2f}"),
                            html.Td(f"{float(r.get('contribution', 0.0)):.2f}"),
                        ]
                    )
                )

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
                dcc.Store(id="sidebar-state", data={"collapsed": False}),
                dcc.Store(id="plotly-resize-signal", data=0),

                # Selection state
                dcc.Store(id="selected-country-store", storage_type="memory"),
                dcc.Store(id="selected-persona-store", data="real_estate", storage_type="memory"),

                # Slider weight state (draft updates immediately, applied updates only on Apply click)
                dcc.Store(id="weights-draft-store", storage_type="memory"),
                dcc.Store(id="weights-applied-store", storage_type="memory"),

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
