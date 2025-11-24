# callbacks/routing_callbacks.py

from dash import Input, Output, html
import dash_bootstrap_components as dbc
import pandas as pd
import requests

from layouts.main_layout import main_layout
from config import API_BASE


def register_routing_callbacks(app, left_panel):

    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname")
    )
    def route_pages(pathname):
        if pathname and pathname.startswith("/report/"):
            report_id = pathname.split("/")[-1]
            return published_report_layout(report_id)

        # Default dashboard
        return main_layout(left_panel)

    def published_report_layout(report_id):
        try:
            res = requests.get(f"{API_BASE}/api/report/{report_id}").json()

            if "error" in res:
                return html.Div("Report not found")

            df = pd.DataFrame(res.get("data", []))

            return html.Div([
                html.H3(f"Published Report {report_id}"),
                dbc.Table.from_dataframe(df, striped=True, bordered=True, hover=True),
                dbc.Button("Back to Dashboard", href="/", color="secondary", className="mt-3")
            ], className="p-3")

        except Exception as e:
            return html.Div(f"Failed to load report: {e}")
