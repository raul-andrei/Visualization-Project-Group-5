from dash import Dash, Input, Output, html, ctx, ALL, dcc
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

        self.register_callbacks()
        self.PERSONA_TO_SCORE = {
            "real_estate": "RE_Opp",
            "agriculture": "Ag_Opp",
            "logistics": "Logistics_Opp",   # ensure scoring produces this name
            "telecom": "Telecom_Opp",
            "fintech": "Fintech_Opp",
            "retail": "Retail_Opp"          # if available
        }

    
    def register_callbacks(self):
        @self.app.callback(
            Output('world-map', 'figure'),
            Input({'type': 'persona-card', 'index': ALL}, 'n_clicks')
        )
        def update_map_on_persona_click(n_clicks_list):
            triggered_id = ctx.triggered_id
            if triggered_id is not None:
                persona_index = triggered_id['index']
                # Logic to update the map based on the selected persona
                # For now, we just print the selected persona
                print(f"Persona selected: {persona_index}")
            # Return the updated figure (for now, return the existing figure)
            return self.map_view.render().children[0].figure
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

            df_plot = scoring_df[["Country", score_col]].dropna().nlargest(5, score_col)
            fig = px.bar(df_plot, x="Country", y=score_col, title=f"Top 5 — {persona}")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=30))
            return dcc.Graph(figure=fig, config={"displayModeBar": False})


    def setup_layout(self):
        """
        Assembles the final page layout by combining all UI components.        
        """
        return html.Div(
            className="app-container", # Defined in assets/style.css
            children=[
                # Render the Sidebar
                self.sidebar.render(),

                # Main Content Area: MapView + AnalyticsPanel
                html.Div(className="map-and-analytics-container",
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