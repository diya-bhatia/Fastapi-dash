# main_layout.py
from dash import html, dcc
import dash_bootstrap_components as dbc
from components.modals import rename_modal

def main_layout(left_panel=None):
    """
    QuickSight-like full layout for Dash:
    - Fixed left panel
    - Main content scrollable
    - Pivot table & chart placeholders
    - Hidden dropdowns & stores for callbacks
    - Modals included
    """

    return html.Div([

        # ----- Left panel -----
        left_panel if left_panel else html.Div(
            id="left-panel",
            children="Left Panel Placeholder",
            style={
                "width": "240px",
                "position": "fixed",
                "top": 0,
                "left": 0,
                "bottom": 0,
                "backgroundColor": "#f8f9fa",
                "padding": "20px"
            }
        ),

        # ----- Main content -----
        html.Div([
            # Dynamic page content (datasets / analyses / dashboards)
            html.Div(id="page-content"),

            # Pivot table & chart areas
            html.Div(id="pivot-table", style={"marginTop": "20px"}),
            html.Div(id="chart-area", style={"marginTop": "20px"}),

            # ----- Hidden dropdowns / inputs for callbacks -----
            dcc.Dropdown(id="table-dataset", options=[], placeholder="Select dataset", style={"display": "none"}),
            dcc.Dropdown(id="table-rows", options=[], multi=True, placeholder="Select table rows", style={"display": "none"}),
            dcc.Dropdown(id="table-cols", options=[], multi=True, placeholder="Select table columns", style={"display": "none"}),
            dcc.Dropdown(id="table-vals", options=[], multi=True, placeholder="Select table values", style={"display": "none"}),
            dcc.Dropdown(
                id="table-aggfunc",
                options=[
                    {"label": "Sum", "value": "sum"},
                    {"label": "Average", "value": "avg"},
                    {"label": "Count", "value": "count"}
                ],
                value="sum",
                style={"display": "none"}
            ),
            dcc.Dropdown(id="chart-dataset", options=[], placeholder="Select chart dataset", style={"display": "none"}),
            dcc.Dropdown(id="chart-rows", options=[], multi=True, placeholder="Select chart rows", style={"display": "none"}),
            dcc.Dropdown(id="chart-vals", options=[], multi=True, placeholder="Select chart values", style={"display": "none"}),

            # ----- Stores for callback states -----
            dcc.Store(id="header_name_map_store", data={}),
            dcc.Store(id="columns_store", data={}),
            dcc.Store(id="last-pivot-config", data={}),
            dcc.Store(id="last-pivot-data", data={}),
            dcc.Store(id="last-pivot-html", data={}),
            dcc.Store(id="calculated_fields_store", data={}),
            dcc.Store(id="calculated_fields_chart_store", data={}),
            dcc.Store(id="store-analyses", data=[]),
            dcc.Store(id="store-dashboards", data=[]),

            # ----- Modals -----
            rename_modal(),

            # ----- Hidden placeholders for callback triggers -----
            html.Div(id="publish-report", style={"display": "none"}),
            html.Div(id="generate-chart", style={"display": "none"}),
            html.Div(id="generate-table", style={"display": "none"}),
            html.Div(id="add-filter-table-btn", style={"display": "none"}),
            html.Div(id="rename-cancel", style={"display": "none"}),
            html.Div(id="rename-save", style={"display": "none"}),

        ], style={
            "marginLeft": "260px",  # leave space for left panel
            "padding": "20px",
            "minHeight": "100vh"
        })
    ])
