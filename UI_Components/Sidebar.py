from dash import dcc, html


class Sidebar:
    def __init__(self):
        # Single source of truth for persona display names / descriptions / accent colors
        self.PERSONAS = {
            "real_estate": {
                "name": "REAL ESTATE",
            },
            "agriculture": {
                "name": "AGRICULTURE",
            },
            "logistics": {
                "name": "TRANSPORT & LOGISTICS",
            },
            "telecom": {
                "name": "TELECOM",
            },
            "fintech": {
                "name": "FINANCIAL SERVICES",
            },
        }

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
                html.Div(
                    className="investor-selector",
                    children=[
                        html.Div("Investor Type", className="investor-selector-label"),
                        dcc.Dropdown(
                            id="persona-dropdown",
                            options=[
                                {"label": v["name"], "value": k}
                                for k, v in self.PERSONAS.items()
                            ],
                            value="real_estate",
                            clearable=False,
                            searchable=False,
                            className="investor-selector-dropdown",
                        ),
                    ],
                ),

                html.Div(className="sidebar-divider"),

                # Sliders will be rendered dynamically depending on the selected persona
                html.Div(
                    id="weights-controls",
                    className="weights-controls",
                    children=[
                        html.Div(
                            className="weights-hint-row",
                            children=[
                                html.Div(
                                    "Adjust attribute importance (1–5), then press Apply.",
                                    className="weights-hint",
                                ),
                                html.Span(
                                    "i",
                                    className="weights-info-icon",
                                    **{"data-tooltip": (
                                        "Country scores are calculated using only the selected attributes, weighted according to your preferences."
                                        " Adjusting weights directly affects rankings and map colors."
                                    )},
                                ),
                            ],
                        ),
                        html.Div(
                            id="weights-sliders-container",
                            className="weights-sliders-container",
                            children=[],
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