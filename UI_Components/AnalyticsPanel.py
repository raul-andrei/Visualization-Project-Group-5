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
                                    id="top-5-chart",
                                    style={"padding": "20px", "color": "white"},
                                    children="Placeholder: Top 5 Chart will render here.",
                                )
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
                                            style={
                                                "display": "flex",
                                                "gap": "10px",
                                                "alignItems": "center",
                                            },
                                            children=[
                                                html.Span(
                                                    "INVESTOR TYPE:",
                                                    style={"color": "#aaa", "fontSize": "12px"},
                                                ),
                                                html.Span(
                                                    id="drilldown-investor-label",
                                                    style={"color": "white", "fontWeight": "bold"},
                                                ),
                                            ],
                                        ),
                                        html.H3(
                                            id="drilldown-country-title",
                                            style={"marginTop": "14px"},
                                        ),

                                        dcc.Loading(
                                            type="default",
                                            children=[
                                                dcc.Graph(
                                                    id="drilldown-splom",
                                                    figure=_dark_placeholder("Click a country on the map to show SPLOM."),
                                                    config={"displayModeBar": False},
                                                ),
                                                dcc.Graph(
                                                    id="drilldown-pcp",
                                                    figure=_dark_placeholder("Click a country on the map to show PCP."),
                                                    config={"displayModeBar": False},
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
