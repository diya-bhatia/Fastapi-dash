from dash import dcc, html
import dash_bootstrap_components as dbc
from components.cards import make_card
from config import AGG_FUNCS

def pivot_layout():
    from components.modals import calc_fields_table_card

    return dbc.Col(
        [
            make_card(
                "Pivot Table Settings",
                [
                    html.Label("Dataset:"),
                    dcc.Dropdown(
                        id="table-dataset",
                        options=[],
                        placeholder="Select dataset",
                        className="mb-2"
                    ),

                    html.Label("Rows:"),
                    dcc.Dropdown(id="table-rows", multi=True, options=[]),

                    html.Label("Columns:"),
                    dcc.Dropdown(id="table-cols", multi=True, options=[]),

                    html.Label("Values:"),
                    dcc.Dropdown(id="table-vals", multi=True, options=[]),

                    html.Label("Aggregation:"),
                    dcc.Dropdown(
                        id="table-aggfunc",
                        options=[{"label": a, "value": a} for a in AGG_FUNCS],
                        value=AGG_FUNCS[0]
                    ),

                    calc_fields_table_card(),

                    html.Label("Filters:"),
                    dbc.Button(
                        "➕ Add Filter",
                        id="add-filter-table-btn",
                        color="secondary",
                        className="mb-2"
                    ),
                    html.Div(id="filters-table-container"),

                    dbc.Button(
                        "Generate Table",
                        id="generate-table",
                        color="primary",
                        className="mt-3 w-100"
                    ),

                    dbc.Button(
                        "Publish Report",
                        id="publish-report",
                        color="success",
                        className="mt-3 w-100"
                    ),

                    html.Div(id="publish-status", className="mt-2")
                ]
            ),

            # <-- THIS IS THE NEW FIX: pivot table output div
            html.Div(id="pivot-table", style={"marginTop": "20px"})
        ],
        width=5
    )
