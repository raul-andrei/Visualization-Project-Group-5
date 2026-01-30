from dash import html, dcc
import plotly.graph_objects as go


def _dark_placeholder(text: str):
    """Dark, transparent placeholder figure (prevents the white empty-graph canvas)."""
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


class AnalyticsPanel:
    def __init__(self):
        pass

    def render(self):
        return html.Div(
            className="custom-tabs-container",
            children=[
                dcc.Tabs(
                    id="analytics-tabs",
                    parent_className="custom-tabs",
                    className="custom-tabs",
                    children=[
                        # TAB 1: LEADERBOARD
                        dcc.Tab(
                            label="LEADERBOARD",
                            value="tab-1",
                            className="tab",
                            selected_className="tab--selected",
                            children=[
                                html.Div(
                                    style={"padding": "16px 20px 0px", "color": "white"},
                                    children=[
                                        html.Div(
                                            style={
                                                "display": "flex",
                                                "alignItems": "center",
                                                "justifyContent": "space-between",
                                                "gap": "12px",
                                                "marginBottom": "10px",
                                            },
                                            children=[
                                                html.Div(
                                                    style={"display": "flex", "flexDirection": "column", "gap": "6px"},
                                                    children=[
                                                        html.Span(
                                                            "SCATTERPLOT",
                                                            style={"color": "#9aa4b2", "fontSize": "11px", "letterSpacing": "0.14em"},
                                                        ),
                                                        html.Span(
                                                            "Score vs selected attribute",
                                                            style={"color": "white", "fontSize": "14px", "fontWeight": 700},
                                                        ),
                                                    ],
                                                ),
                                                html.Div(
                                                    style={"minWidth": "260px"},
                                                    children=[
                                                        dcc.Dropdown(
                                                            id="scatter-y-attr",
                                                            options=[
                                                                {"label": "GDP per Capita (k USD)", "value": "Real_GDP_per_Capita_USD"},
                                                                {"label": "Population (M)", "value": "Total_Population"},
                                                                {"label": "Population Growth (%)", "value": "Population_Growth_Rate"},
                                                                {"label": "Net Migration Rate", "value": "Net_Migration_Rate"},
                                                                {"label": "Unemployment (%)", "value": "Unemployment_Rate_percent"},
                                                                {"label": "Public Debt (% of GDP)", "value": "Public_Debt_percent_of_GDP"},
                                                            ],
                                                            value="Real_GDP_per_Capita_USD",
                                                            clearable=False,
                                                            searchable=False,
                                                            className="investor-selector-dropdown",
                                                        )
                                                    ],
                                                ),
                                            ],
                                        ),
                                        dcc.Graph(
                                            id="score-attr-scatter",
                                            figure=_dark_placeholder("Adjust filters and press Apply to update the scatter plot."),
                                            config={"displayModeBar": False},
                                            style={"height": "360px"},
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="sidebar-divider",
                                    style={"width": "100%", "max-width": "1400px", "margin-top": "30px", "margin-bottom": "40px"},
                                ),
                                html.Div(
                                    style={"display": "flex", "flexDirection": "column", "gap": "6px", "padding": "0px 20px 0px", "color": "white"},
                                    children=[
                                        html.Span(
                                            "LEADERBOARD",
                                            style={"color": "#9aa4b2", "fontSize": "11px", "letterSpacing": "0.14em"},
                                        ),
                                        html.Span(
                                            "Top 5 countries by opportunity score",
                                            style={"color": "white", "fontSize": "14px", "fontWeight": 700},
                                        ),
                                    ],
                                ),
                                html.Div(
                                    id="top-5-chart",
                                    style={"padding": "10px 20px 20px", "color": "white"},
                                    children=[],
                                ),
                            ],
                        ),

                        # TAB 3: COUNTRY DRILLDOWN
                        dcc.Tab(
                            label="COUNTRY DRILLDOWN",
                            value="tab-3",
                            className="tab",
                            selected_className="tab--selected",
                            children=[
                                html.Div(
                                    style={"padding": "20px", "color": "white"},
                                    children=[
                                        html.Div(
                                            style={"display": "flex", "gap": "10px", "alignItems": "center"},
                                            children=[
                                                html.Span("INVESTOR TYPE:", style={"color": "#aaa", "fontSize": "12px"}),
                                                html.Span(
                                                    id="drilldown-investor-label",
                                                    style={"color": "white", "fontWeight": "bold"},
                                                ),
                                            ],
                                        ),
                                        html.H3(id="drilldown-country-title", style={"marginTop": "14px"}),

                                        dcc.Loading(
                                            type="default",
                                            children=[
                                                #Radar
                                                dcc.Graph(
                                                    id="drilldown-radar",
                                                    figure=_dark_placeholder("Click a country on the map to show radar + values."),
                                                    config={"displayModeBar": False},
                                                    style={"height": "380px"},
                                                ),

                                                #exact values panel
                                                html.Div(
                                                    id="drilldown-values",
                                                    style={
                                                        "marginTop": "10px",
                                                        "padding": "12px 14px",
                                                        "border": "1px solid rgba(255,255,255,0.10)",
                                                        "borderRadius": "10px",
                                                        "background": "rgba(0,0,0,0.15)",
                                                    },
                                                    children=[
                                                        html.Div(
                                                            style={"color": "#9aa4b2", "fontSize": "12px"},
                                                            children="Exact values will appear after selecting a country.",
                                                        )
                                                    ],
                                                ),

                                                
                                                dcc.Graph(
                                                    id="drilldown-pcp",
                                                    figure=_dark_placeholder("Click a country on the map to show PCP."),
                                                    config={"displayModeBar": False},
                                                    style = {"height" :"240px" , "width" : "100%"},
                                                ),
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
