from dash import dcc, html

class Sidebar:
    def __init__(self):
        self.PERSONAS = {
            'real_estate': {
                'name': 'REAL ESTATE',
                'desc': 'High population density, stability, and wealth.',
                'color': '#66fcf1'
            },
            'agriculture': {
                'name': 'AGRICULTURE',
                'desc': 'Land availability, labor force, and resources.',
                'color': '#22c55e'
            },
            'logistics': {
                'name': 'TRANSPORT & LOGISTICS',
                'desc': 'Trade hubs with strong infrastructure.',
                'color': '#fb923c'
            },
            'telecom': {
                'name': 'TELECOM',
                'desc': 'High tech adoption and urbanization.',
                'color': '#d946ef'
            },
            'fintech': {
                'name': 'FINANCIAL SERVICES',
                'desc': 'Wealthy markets with digital readiness.',
                'color': '#3b82f6'
            }
        }

    def render(self):
        """
        Returns the main layout for the left side.
        """
        return html.Div(
            className="sidebar",
            children=[
                html.Div(
                    className="sidebar",
                    children=[
                        self.render_logo(),
                        self.render_controls()
                    ]
                )
            ]
        )
    def render_logo(self):
        """
        Returns the logo section of the sidebar.
        """
        return html.Div(
            className="logo-section",
            children=[
                # Logo for later use
                #html.Img(
                #    src="/assets/logo.png",
                #   className="logo-image"
                #),
                html.H1(
                    "NEXUS SCOUT",
                    className="logo-title"
                ),
                html.Div(
                    "Global Capital Allocation Engine", 
                     className="logo-subtitle"
                     )
            ]
        )
    def render_controls(self):
        """
        Creates the scrollable controls area
        """
        return html.Div(
            style={'flex': '1', 'overflowY': 'auto', 'padding': '20px'},
            children=[
                html.Label("INVESTOR PROTOCOL", className="section-label"),
                
                # 1. Persona Cards Container
                html.Div(
                    className="persona-container",
                    children=[
                        # We loop through our data to create cards
                        self.build_card(key, data) for key, data in self.PERSONAS.items()
                    ]
                ),

                html.Div(style={'height': '40px'}), # Spacer

                html.Label("GEOGRAPHIC FILTER", className="section-label"),
                
                # 2. Region Dropdown
                dcc.Dropdown(
                    id='region-filter',
                    options=[
                        {'label': 'Global View', 'value': 'all'},
                        {'label': 'North America', 'value': 'na'},
                        {'label': 'Europe', 'value': 'eu'},
                        {'label': 'Asia Pacific', 'value': 'apac'}
                    ],
                    value='all',
                    clearable=False,
                    className='custom-dropdown'
                ),
            ]
        )

    def build_card(self, key, data):
        """
        Creates a single card component.
        """
        return html.Div(
            id={'type': 'persona-card', 'index': key}, # Special ID for pattern matching
            className="persona-card",
            style={'--active-color': data['color']}, # Pass color to CSS variable
            children=[
                html.Div(className="persona-header", children=[
                    html.Span(data['name'], className="persona-name"),
                    # The little colored dot
                    html.Div(style={
                        'width': '8px', 'height': '8px', 
                        'borderRadius': '50%', 
                        'backgroundColor': data['color'],
                        'boxShadow': f"0 0 8px {data['color']}"
                    })
                ]),
                html.Div(data['desc'], className="persona-desc")
            ]
        )