from dash import dcc, html
import dash_bootstrap_components as dbc
from config import AGG_FUNCS

def chart_layout():
    from components.modals import calc_fields_chart_card
    return dbc.Modal(
        [
            dbc.ModalHeader("Chart Settings"),
            dbc.ModalBody([
                html.Label("Dataset:"),
                dcc.Dropdown(id="chart-dataset"),

                html.Label("X-axis:"),
                dcc.Dropdown(id="chart-rows"),

                html.Label("Values:"),
                dcc.Dropdown(id="chart-vals", multi=True),

                html.Label("Aggregation:"),
                dcc.Dropdown(
                    id="chart-aggfunc",
                    options=[{"label": a, "value": a} for a in AGG_FUNCS],
                    value=AGG_FUNCS[0]
                ),

                calc_fields_chart_card()
            ]),
            dbc.ModalFooter([
                dbc.Button("Generate Chart", id="generate-chart", color="success"),
                dbc.Button("Close", id="close-chart-modal")
            ])
        ],
        id="chart-settings-modal",
        is_open=False,
        size="lg"
    )
