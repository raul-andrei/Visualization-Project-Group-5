from dash import html, dcc
import plotly.express as px

class MapView:
    def __init__(self):
        pass

    def render(self):
        """
        Returns the layout for the Map section.
        """
        return html.Div(
            className="map-container",
            children=[
                # This Graph component is where Plotly draws the map
                dcc.Graph(
                    id='world-map',
                    # We configure it to look good before data arrives
                    config={'displayModeBar': False, 'scrollZoom': False},
                    style={'height': '100%', 'width': '100%'}
                ),
                
                # A visual overlay helper (optional design touch)
                html.Div(
                    style={
                        'position': 'absolute', 'top': '20px', 'right': '20px', 
                        'padding': '10px 20px', 'background': 'rgba(0,0,0,0.8)', 
                        'borderRadius': '4px', 'border': '1px solid #66fcf1',
                        'color': '#aaa', 'pointerEvents': 'none'
                    }, 
                    children="STATUS: WAITING FOR DATA"
                )
            ]
        )