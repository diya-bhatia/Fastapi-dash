from dash import Input, Output, State, callback_context, html
import dash_bootstrap_components as dbc
from layouts.stores_layout import stores_layout
from layouts.pivot_table import pivot_layout
from layouts.chart import chart_layout
from app import app  # your Dash instance

@app.callback(
    Output("page-content", "children"),
    [
        Input("new-analysis-btn", "n_clicks"),
        Input("dashboards-btn", "n_clicks"),
        Input("datasets-btn", "n_clicks")
    ],
    [
        State("store-analyses", "data"),
        State("store-dashboards", "data")
    ]
)
def display_page(new_analysis, dashboards_click, datasets_click, analyses, dashboards):
    ctx = callback_context
    if not ctx.triggered:
        # Initial landing page
        return html.H3("Welcome! Select a section from the left panel.")

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "datasets-btn":
        # Show datasets
        return html.Div(stores_layout())

    elif button_id == "new-analysis-btn":
        # Show pivot table + chart for new analysis
        return html.Div([
            dbc.Row([
                dbc.Col(dbc.Button("⚙️ Pivot Settings", id="open-pivot-modal"), width="auto"),
                dbc.Col(dbc.Button("📈 Chart Settings", id="open-chart-modal"), width="auto"),
                dbc.Col(dbc.Button("💾 Publish Report", id="publish-btn", color="success"), width="auto")
            ], className="mb-3"),

            # Include pivot_table and chart placeholders
            html.Div(id="pivot-table"),
            html.Div(id="chart-area")
        ])

    elif button_id == "dashboards-btn":
        if dashboards:
            return html.Div([
                html.H4("Published Dashboards"),
                html.Ul([html.Li(d) for d in dashboards])
            ])
        return html.H4("No dashboards published yet.")
