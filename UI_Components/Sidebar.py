from dash import dcc, html

REAL_ESTATE_FILTERS = [
    {"col": "Real_GDP_per_Capita_USD", "label": "GDP per Capita (USD)", "dir": +1},
    {"col": "Total_Population", "label": "Population", "dir": +1},
    {"col": "Population_Growth_Rate", "label": "Population Growth (%)", "dir": +1},
    {"col": "Net_Migration_Rate", "label": "Net Migration Rate (%)", "dir": +1},
    {"col": "Unemployment_Rate_percent", "label": "Unemployment (%)", "dir": -1},
    {"col": "Public_Debt_percent_of_GDP", "label": "Public Debt (% of GDP)", "dir": -1},
]

# Human-friendly slider ranges (Option A)
# Keep values in raw units (USD, people, %, etc.), but rounded for UI.
FILTER_SLIDER_SPECS = {
    "Real_GDP_per_Capita_USD": {
        # UI in k USD (so 120 means 120,000 USD)
        "min": 0,
        "max": 120,
        "step": 1,
        "value": [0, 120],
    },
    "Total_Population": {
        # UI in millions (so 1500 means 1.5B people)
        "min": 0,
        "max": 1500,
        "step": 10,
        "value": [0, 1500],
    },
    "Population_Growth_Rate": {
        "min": 0.0,
        "max": 7.0,
        "step": 0.1,
        "value": [0.0, 7.0],
    },
    "Net_Migration_Rate": {
        "min": -5.0,
        "max": 50.0,
        "step": 0.5,
        "value": [-5.0, 50.0],
    },
    "Unemployment_Rate_percent": {
        "min": 0.0,
        "max": 40.0,
        "step": 0.5,
        "value": [0.0, 40.0],
    },
    "Public_Debt_percent_of_GDP": {
        "min": 0.0,
        "max": 300.0,
        "step": 5.0,
        "value": [0.0, 300.0],
    },
}

# UI display helpers (no effect on algorithm)
FILTER_UI_FORMAT = {
    "Real_GDP_per_Capita_USD": {"scale": 1.0, "suffix": "k USD"},
    "Total_Population": {"scale": 1.0, "suffix": "M"},
    "Population_Growth_Rate": {"scale": 1.0, "suffix": "%"},
    "Net_Migration_Rate": {"scale": 1.0, "suffix": "%"},
    "Unemployment_Rate_percent": {"scale": 1.0, "suffix": "%"},
    "Public_Debt_percent_of_GDP": {"scale": 1.0, "suffix": "%"},
}

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

    # Top + Navigation
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

    # Panel area (expanded content)
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
                                                    "—",
                                                    id={"type": "filter-range-value", "col": f["col"]},
                                                    className="weight-slider-value",
                                                ),
                                            ],
                                        ),
                                        dcc.RangeSlider(
                                            id={"type": "filter-range", "col": f["col"]},
                                            min=FILTER_SLIDER_SPECS[f["col"]]["min"],
                                            max=FILTER_SLIDER_SPECS[f["col"]]["max"],
                                            step=FILTER_SLIDER_SPECS[f["col"]]["step"],
                                            value=FILTER_SLIDER_SPECS[f["col"]]["value"],
                                            marks=None,
                                            tooltip={
                                                "placement": "bottom",
                                                "always_visible": False,
                                                "template": f"{{value}}{FILTER_UI_FORMAT[f['col']]['suffix']}",
                                            },
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