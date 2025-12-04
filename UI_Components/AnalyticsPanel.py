from dash import html, dcc

class AnalyticsPanel:
    def __init__(self):
        pass

    def render(self):
        """
        Returns the layout for the bottom analytics section (Tabs).
        """
        return html.Div(
            className="custom-tabs-container",
            children=[
                dcc.Tabs(
                    id='analytics-tabs',
                    parent_className='custom-tabs',
                    className='custom-tabs',
                    children=[
                        # TAB 1: LEADERBOARD
                        dcc.Tab(
                            label='LEADERBOARD', 
                            value='tab-1',
                            className='tab', 
                            selected_className='tab--selected', 
                            children=[
                                html.Div(
                                    id='top-5-chart', # Main.py will look for this ID later
                                    style={'padding': '20px', 'color': 'white'},
                                    children="Placeholder: Top 5 Chart will render here."
                                )
                            ]
                        ),
                        
                        # TAB 2: COMPARISON
                        dcc.Tab(
                            label='COMPARISON ENGINE', 
                            value='tab-2',
                            className='tab', 
                            selected_className='tab--selected', 
                            children=[
                                html.Div(
                                    id='comparison-radar', # Main.py will look for this ID later
                                    style={'padding': '20px', 'color': 'white'},
                                    children="Placeholder: Radar Chart will render here."
                                )
                            ]
                        ),
                        
                        # TAB 3: RISK MATRIX
                        dcc.Tab(
                            label='RISK MATRIX', 
                            value='tab-3',
                            className='tab', 
                            selected_className='tab--selected', 
                            children=[
                                html.Div(
                                    id='risk-scatter', # Main.py will look for this ID later
                                    style={'padding': '20px', 'color': 'white'},
                                    children="Placeholder: Scatter Plot will render here."
                                )
                            ]
                        ),
                    ]
                )
            ]
        )