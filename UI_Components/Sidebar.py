from dash import dcc, html

REAL_ESTATE_FILTERS = [
    {"col": "Real_GDP_per_Capita_USD", "label": "GDP per Capita (USD)", "dir": +1},
    {"col": "Total_Population", "label": "Population", "dir": +1},
    {"col": "Population_Growth_Rate", "label": "Population Growth (%)", "dir": +1},
    {"col": "Net_Migration_Rate", "label": "Net Migration Rate", "dir": +1},
    {"col": "Unemployment_Rate_percent", "label": "Unemployment (%)", "dir": -1},
    {"col": "Public_Debt_percent_of_GDP", "label": "Public Debt (% of GDP)", "dir": -1},
]

class Sidebar:
    def __init__(self):
        pass

    def render(self):
        """Returns the full sidebar layout (icon rail + expandable panel)."""
        return html.Div(
            id="sidebar-wrapper",
            className="sidebar",
            children=[
                self.render_topbar(),
                html.Div(className="sidebar-divider"),
                self.render_panel_area(),
            ],
        )

    # -------------------------
    # Top + Navigation
    # -------------------------
    def render_topbar(self):
        """Top bar: collapse/expand button + app branding (branding hidden in collapsed mode via CSS)."""
        return html.Div(
            className="sidebar-topbar",
            children=[
                html.Button(
                    "☰",
                    id="sidebar-collapse-btn",
                    className="sidebar-icon-btn",
                    n_clicks=0,
                    title="Collapse / Expand",
                ),
                html.Div(
                    className="sidebar-brand",
                    children=[
                        html.Div("NEXUS SCOUT", className="sidebar-brand-title"),
                    ],
                ),
            ],
        )

    # -------------------------
    # Panel area (expanded content)
    # -------------------------
    def render_panel_area(self):
        """Container for the active panel. Which panel is visible will be controlled via callbacks/CSS."""
        return html.Div(
            id="sidebar-panel-area",
            className="sidebar-panel-area",
            children=[
                self.render_panel_investors(),
            ],
        )

    def render_panel_investors(self):
        return html.Div(
            id="sidebar-panel-investors",
            className="sidebar-panel sidebar-panel--active",  # default active panel
            children=[
                
                # Sliders will be rendered dynamically depending on the selected persona
                html.Div(
                    id="weights-controls",
                    className="weights-controls",
                    children=[
                        html.Div(
                            className="weights-hint-row",
                            children=[
                                html.Div(
                                    "Filter countries by setting min/max ranges for each attribute, then press Apply.",
                                    className="weights-hint",
                                ),
                                html.Span(
                                    "i",
                                    className="weights-info-icon",
                                    **{"data-tooltip": (
                                        "Use these sliders to filter the dataset. Countries outside any selected range are hidden. Press Apply to update the map and charts."
                                    )},
                                ),
                            ],
                        ),
                        html.Div(
                            id="weights-sliders-container",
                            className="weights-sliders-container",
                            children=[
                                html.Div(
                                    className="weight-slider",
                                    children=[
                                        html.Div(
                                            className="weight-slider-header",
                                            children=[
                                                html.Span(f["label"], className="weight-slider-label"),
                                                html.Span(
                                                    "",
                                                    id={"type": "filter-range-value", "col": f["col"]},
                                                    className="weight-slider-value",
                                                ),
                                            ],
                                        ),
                                        dcc.RangeSlider(
                                            id={"type": "filter-range", "col": f["col"]},
                                            min=0,
                                            max=100,
                                            step=1,
                                            value=[0, 100],
                                            marks=None,
                                            tooltip={"placement": "bottom", "always_visible": False},
                                            className="weight-slider-control",
                                            allowCross=False,
                                        ),
                                    ],
                                )
                                for f in REAL_ESTATE_FILTERS
                            ],
                        ),
                        html.Button(
                            "Apply",
                            id="apply-weights-btn",
                            n_clicks=0,
                            className="weights-apply-btn",
                        ),
                    ],
                ),
            ],
        )