from dash import html, dcc

class AnalyticsPanel:
    def __init__(self):
        pass

    def render(self):
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
                                    id='top-5-chart',
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
                                    id='comparison-radar',
                                    style={'padding': '20px', 'color': 'white'},
                                    children="Placeholder: Radar Chart will render here."
                                )
                            ]
                        ),

                        # TAB 3: COUNTRY DRILLDOWN
                        dcc.Tab(
                            label='COUNTRY DRILLDOWN',
                            value='tab-3',
                            className='tab',
                            selected_className='tab--selected',
                            children=[
                                html.Div(
                                    style={'padding': '20px', 'color': 'white'},
                                    children=[
                                        html.Div(
                                            style={'display': 'flex', 'gap': '12px', 'alignItems': 'center'},
                                            children=[
                                                html.Div(
                                                    style={'display': 'flex', 'gap': '10px', 'alignItems': 'center'},
                                                    children=[
                                                        html.Span("INVESTOR TYPE:", style={'color': '#aaa', 'fontSize': '12px'}),
                                                        html.Span(id="drilldown-investor-label", style={'color': 'white', 'fontWeight': 'bold'}),
                                                    ]


                                                ),




                                                
                                            ],
                                        ),
                                        html.H3(id="drilldown-country-title", style={'marginTop': '14px'}),
                                        dcc.Loading(
                                            type="default",
                                            children=[
                                                dcc.Graph(
                                                    id="drilldown-breakdown-chart",
                                                    config={"displayModeBar": False},
                                                ),
                                                html.Div(id="drilldown-breakdown-table", style={'marginTop': '10px'}),
                                            ],
                                        ),
                                    ],
                                )
                            ],
                        ),
                    ],
                )
            ],
        )
