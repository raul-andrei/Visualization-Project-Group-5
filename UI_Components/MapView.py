from dash import html, dcc
import plotly.express as px
import plotly.graph_objects as go

class MapView:
    def __init__(self):
        pass

    def render(self):
        """
        Returns the layout for the Map section.
        """
        fig = go.Figure(go.Scattergeo())
        fig.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0},
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
                projection_type="natural earth" 
            ),
            dragmode=False
        )


        return html.Div(
            className="map-container",
            children=[
                dcc.Graph(
                    id='world-map',
                    figure=fig,
                    className='map-graph',
                    config={'displayModeBar': False, 'scrollZoom': True, 'showTips': False},
                    
                ),
                html.Div(
                className="map-overlay",
                children=[
                    html.Span("INTERACTION MODE: ", style={'color': '#aaa'}),
                    html.Span("DOUBLE-CLICK to Reset ", style={'color': '#fff', 'fontWeight': 'bold'})
                ]
            )
                
            ]
        )