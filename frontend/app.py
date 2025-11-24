# app.py

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc

from components.left_panel import build_left_panel
from layouts.main_layout import main_layout
from callbacks import register_all_callbacks
from callbacks.routing_callbacks import register_routing_callbacks
from callbacks import navigation  # registers display_page

# ---- Initialize Dash app ----
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True  # Needed for dynamic callbacks
)

# ---- Build Sidebar ----
left_panel = build_left_panel()

# ---- App Layout ----
app.layout = html.Div([
    # Multi-page support
    dcc.Location(id="url"),
    html.Div(id="page-content"),

    # Client-side stores
    dcc.Store(id="columns_store", data={}),
    dcc.Store(id="last-pivot-config", data={}),
    dcc.Store(id="last-pivot-data", data={}),
    dcc.Store(id="calculated_fields_store", data={}),
    dcc.Store(id="calculated_fields_chart_store", data={}),

    # Hidden placeholders for dynamic components
    html.Div(id="rename-cancel", style={"display": "none"}),
    html.Div(id="rename-save", style={"display": "none"}),
    html.Div(id="add-calc-field-chart", style={"display": "none"}),
    html.Div(id="add-calc-field-table", style={"display": "none"})
])

# ---- Register Callbacks ----
register_all_callbacks(app)                  # Your main callbacks
register_routing_callbacks(app, left_panel)  # Routing callbacks

# ---- Run App ----
if __name__ == "__main__":
    app.run(debug=True, port=8050)
