from dash import Dash, Input, Output, State, html, ctx, ALL, dcc
from dash.exceptions import PreventUpdate
from UI_Components.Sidebar import Sidebar
from UI_Components.MapView import MapView
from UI_Components.AnalyticsPanel import AnalyticsPanel
from scoring import load_and_process_data
from plotly import express as px 
from plotly import graph_objects as go

scoring_df = load_and_process_data()


class Main:
    
    def __init__(self):
        self.app = Dash(__name__)
        self.app.title = "NEXUS SCOUT"

        self.sidebar = Sidebar()
        self.map_view = MapView()
        self.analytics_panel = AnalyticsPanel()

        self.app.layout = self.setup_layout()

        # Force Plotly to relayout smoothly during sidebar collapse/expand
        self.app.clientside_callback(
            """
            function(state) {
                // Dispatch resize events during the sidebar animation
                const delays = [0, 50, 120, 200, 300, 420];
                delays.forEach(d => setTimeout(() => window.dispatchEvent(new Event('resize')), d));
                return Date.now();
            }
            """,
            Output("plotly-resize-signal", "data"),
            Input("sidebar-state", "data"),
        )

        self.PERSONA_TO_SCORE = {
            "real_estate": "RE_Opp",
            "agriculture": "Ag_Opp",
            "logistics": "Logistics_Opp",  
            "telecom": "Telecom_Opp",
            "fintech": "Fintech_Opp",
            "retail": "Retail_Opp"          
        }

        self.PERSONAS = Sidebar().PERSONAS

        self.register_callbacks()

    
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

            # 1) Collapse button toggles collapsed state
            if trigger == "sidebar-collapse-btn":
                state["collapsed"] = not state.get("collapsed", False)
                return state

            # 2) Nav item pressed -> set active panel (and auto-expand if collapsed)
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

            # Sidebar collapse state
            sidebar_class = "sidebar sidebar--collapsed" if collapsed else "sidebar"

            content_class = (
                "map-and-analytics-container map-and-analytics-container--collapsed"
                if collapsed
                else "map-and-analytics-container"
            )

            # Panel visibility
            def panel_class(key):
                base = "sidebar-panel"
                return f"{base} sidebar-panel--active" if active == key else base

            # Active nav highlight
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

        @self.app.callback(
            Output("world-map", "figure"),
            Input({"type": "persona-card", "index": ALL}, "n_clicks"),
        )
        def update_map_on_persona_click(n_clicks_list):
            """
            Update the choropleth map when a persona card is clicked.
            Uses scoring_df and PERSONA_TO_SCORE.
            """
            # 1. Work out which persona is active
            trigger = ctx.triggered_id  # e.g. {"type": "persona-card", "index": "agriculture"}

            if trigger and isinstance(trigger, dict):
                persona = trigger.get("index", "real_estate")
            else:
                # initial page load / no clicks yet
                persona = "real_estate"

            # 2. Map persona -> score column
            score_col = self.PERSONA_TO_SCORE.get(persona)
            if not score_col or score_col not in scoring_df.columns:
                # no score for this persona: return base world map
                return self._empty_world_figure()

            # 3. Prepare data for the map
            df_plot = scoring_df[["Country", score_col]].dropna()
            if df_plot.empty:
                return self._empty_world_figure()

            # 4. Build choropleth
            fig = px.choropleth(
                df_plot,
                locations="Country",
                locationmode="country names",
                color=score_col,
                hover_name="Country",
                title=f"<b>{self.PERSONAS[persona]['name']}<b>",
            )

            # 5. Apply your dark styling (same as MapView)
            fig.update_layout(
                title_font=dict(
                    family="Inter, sans-serif",
                    size=22,
                    color="white"
                ),
                font=dict(
                    family="Inter, sans-serif",
                    color="white"   # axis labels, hover etc.
                ),
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

        @self.app.callback(
            Output("top-5-chart", "children"),
            Input({"type": "persona-card", "index": ALL}, "n_clicks")
)
        def top5(persona_n_clicks):
            trigger = ctx.triggered_id
            persona = trigger.get("index") if trigger else "real_estate"
            score_col = self.PERSONA_TO_SCORE.get(persona)
            if not score_col or score_col not in scoring_df.columns:
                return "No data"

            # Top 5 bar chart
            df_top = scoring_df[["Country", score_col]].dropna().nlargest(5, score_col)
            bar_fig = px.bar(
                df_top,
                x="Country",
                y=score_col,
                title=f"Top 5 — {self.PERSONAS[persona]['name']}",
            )
            bar_fig.update_layout(
                title_font=dict(
                    family="Inter, sans-serif",
                    size=22,
                    color="white"
                ),
                font=dict(
                    family="Inter, sans-serif",
                    color="white"   # axis labels, hover etc.
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                margin=dict(t=60),
            )

            # Neural map scatter (PCA_1 / PCA_2 from neural_engine or PCA fallback)
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
                scatter_fig.update_layout(
                    title_font=dict(
                    family="Inter, sans-serif",
                    size=22,
                    color="white"
                ),
                font=dict(
                    family="Inter, sans-serif",
                    color="white"   # axis labels, hover etc.
                ),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="white",
                    margin=dict(t=60),
                )

                return html.Div([
                    dcc.Graph(figure=bar_fig, config={"displayModeBar": False}),
                    dcc.Graph(figure=scatter_fig, config={"displayModeBar": False}),
                ])

            # Fallback: only bar chart if PCA/Neural coords are missing
            return dcc.Graph(figure=bar_fig, config={"displayModeBar": False})


    def setup_layout(self):
        """
        Assembles the final page layout by combining all UI components.        
        """
        return html.Div(
            className="app-container", # Defined in assets/style.css
            children=[
                # Sidebar UI state (collapsed + active panel)
                dcc.Store(id="sidebar-state", data={"collapsed": False, "active": "investors"}),
                dcc.Store(id="plotly-resize-signal", data=0),

                # Render the Sidebar
                self.sidebar.render(),

                # Main Content Area: MapView + AnalyticsPanel
                html.Div(
                    id="map-and-analytics-container",
                    className="map-and-analytics-container",
                    children=[
                        # Render the Main Content Area (MapView)
                        self.map_view.render(),
                        # Render the Analytics Panel below the MapView
                        self.analytics_panel.render()
                    ]
                )
            ]
        )
    

    def run(self):
        self.app.run(debug=True, dev_tools_ui=False)

if __name__ == '__main__':
    main = Main()
    main.run()