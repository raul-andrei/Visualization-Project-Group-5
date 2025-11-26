from dash import html

class Sidebar:
    def __init__(self):
        pass

    def render(self):
        """
        Returns the layout for the left side.
        """
        return html.Div(
            className="sidebar",
            children=[
                # 1. The Logo Section
                html.Div(
                    className="logo-section",
                    children=[
                        html.H1("NEXUS SCOUT", className="logo-title"),
                        html.Div("Global Investment Engine", className="logo-subtitle")
                    ]
                ),
                
                # 2. The Controls Section (Placeholder for now)
                html.Div(
                    style={'padding': '20px', 'color': 'white'},
                    children=[
                        html.P("Controls will go here...")
                    ]
                )
            ]
        )