from dash import Input, Output, State, html
import requests
from config import PUBLISH_URL

def register_publish_callbacks(app):

    @app.callback(
        Output("publish-status", "children"),
        Input("publish-report", "n_clicks"),
        State("last-pivot-html", "data"),
        State("last-pivot-data", "data"),
        State("last-pivot-config", "data"),
        prevent_initial_call=True
    )
    def publish_report(n, pivot_html, data, config):
        if not pivot_html or not data or not config:
            return "Generate report first"

        try:
            res = requests.post(PUBLISH_URL, json={
                "report_html": pivot_html,   # contains renamed headers
                "report_config": config,
                "report_data": data
            }).json()

            rid = res.get("report_id")
            return html.A(
                "View Published Report",
                href=f"/report/{rid}",
                target="_blank",
                style={"color": "#670178", "fontWeight": "bold"}
            )

        except Exception as e:
            return f"Error: {str(e)}"
