from dash import dcc, html


class Sidebar:
    def __init__(self):
        # Single source of truth for persona display names / descriptions / accent colors
        self.PERSONAS = {
            "real_estate": {
                "name": "REAL ESTATE",
                "desc": "High population density, stability, and wealth.",
                "color": "#66fcf1",
            },
            "agriculture": {
                "name": "AGRICULTURE",
                "desc": "Land availability, labor force, and resources.",
                "color": "#22c55e",
            },
            "logistics": {
                "name": "TRANSPORT & LOGISTICS",
                "desc": "Trade hubs with strong infrastructure.",
                "color": "#fb923c",
            },
            "telecom": {
                "name": "TELECOM",
                "desc": "High tech adoption and urbanization.",
                "color": "#d946ef",
            },
            "fintech": {
                "name": "FINANCIAL SERVICES",
                "desc": "Wealthy markets with digital readiness.",
                "color": "#3b82f6",
            },
        }

    def render(self):
        """Returns the full sidebar layout (icon rail + expandable panel)."""
        return html.Div(
            id="sidebar-wrapper",
            className="sidebar",  # CSS will later switch to 'sidebar sidebar--collapsed'
            children=[
                self.render_topbar(),
                self.render_nav_rail(),
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

    def render_nav_rail(self):
        """Icon rail that is always visible (expanded: icon + label via CSS; collapsed: icon only)."""
        return html.Div(
            className="sidebar-nav",
            children=[
                self._nav_item("investors", "/assets/icons/investors.png", "Investor Protocol"),
                self._nav_item("geo", "/assets/icons/geo.png", "Geographic Filter"),
                self._nav_item("bookmarks", "/assets/icons/bookmarks.png", "Bookmarks"),
            ],
        )

    def _nav_item(self, key: str, icon: str, label: str):
        """One nav item. We use a real button so it has n_clicks for callbacks."""
        return html.Button(
            children=[
                html.Img(src=icon, className="sidebar-nav-icon"),
                html.Span(label, className="sidebar-nav-label"),
            ],
            id={"type": "sidebar-nav", "index": key},
            className="sidebar-nav-item",  # callback can add 'sidebar-nav-item sidebar-nav-item--active'
            n_clicks=0,
            title=label,  # tooltip (important in collapsed mode)
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
                html.Div(className="sidebar-divider"),
                self.render_panel_investors(),
                self.render_panel_geo(),
                self.render_panel_bookmarks(),
            ],
        )

    def render_panel_investors(self):
        return html.Div(
            id="sidebar-panel-investors",
            className="sidebar-panel sidebar-panel--active",  # default active panel
            children=[
                html.Div(
                    className="persona-container",
                    children=[self.build_card(key, data) for key, data in self.PERSONAS.items()],
                ),

                # Sliders will be rendered dynamically depending on the selected persona
                html.Div(
                    id="weights-controls",
                    className="weights-controls",
                    children=[
                        html.Div(
                            "Adjust attribute importance (1–5), then press Apply.",
                            className="weights-hint",
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

    def render_panel_geo(self):
        return html.Div(
            id="sidebar-panel-geo",
            className="sidebar-panel",  # hidden by default until selected
            children=[
                dcc.Dropdown(
                    id="geo-filter",
                    options=[
                        {"label": "Global View", "value": "Global View"},
                        {"label": "North America", "value": "North America"},
                        {"label": "Europe", "value": "Europe"},
                        {"label": "Asia Pacific", "value": "Asia Pacific"},
                    ],
                    value="Global View",
                    clearable=False,
                    className="custom-dropdown",
                ),
            ],
        )

    def render_panel_bookmarks(self):
        # Placeholder: you will implement later.
        return html.Div(
            id="sidebar-panel-bookmarks",
            className="sidebar-panel",
            children=[
                html.Div(
                    "Coming soon: save countries to a shortlist for later comparison.",
                    className="sidebar-placeholder",
                ),
            ],
        )

    # -------------------------
    # Persona cards
    # -------------------------
    def build_card(self, key, data):
        """Creates a single persona card component."""
        return html.Div(
            id={"type": "persona-card", "index": key},
            className="persona-card",
            style={"--active-color": data["color"]},
            children=[
                html.Div(
                    className="persona-header",
                    children=[
                        html.Span(data["name"], className="persona-name"),
                        html.Div(
                            style={
                                "width": "8px",
                                "height": "8px",
                                "borderRadius": "50%",
                                "backgroundColor": data["color"],
                                "boxShadow": f"0 0 8px {data['color']}",
                            }
                        ),
                    ],
                ),
            ],
        )