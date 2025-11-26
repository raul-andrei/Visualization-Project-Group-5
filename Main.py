from dash import Dash, html
from UI_Components.Sidebar import Sidebar
from UI_Components.MapView import MapView
from UI_Components.AnalyticsPanel import AnalyticsPanel

class Main:
    def __init__(self):
        self.app = Dash(__name__)
        self.app.title = "NEXUS SCOUT"

        self.sidebar = Sidebar()
        self.map_view = MapView()
        self.analytics_panel = AnalyticsPanel()

        self.app.layout = self.setup_layout()

    def setup_layout(self):
        """
        Assembles the final page layout by combining all UI components.        
        """
        return html.Div(
            className="app-container", # Defined in assets/style.css
            children=[
                # Render the Sidebar
                self.sidebar.render(),
                
                # Render the Main Content Area (MapView)
                self.map_view.render(),

                # Render the Analytics Panel at the bottom
                self.analytics_panel.render()
            ]
        )

    def run(self):
        self.app.run(debug=True)

if __name__ == '__main__':
    main = Main()
    main.run()