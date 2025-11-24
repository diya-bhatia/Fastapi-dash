from dash import dcc, html, Input, Output, State, ALL, ctx, no_update
import dash_bootstrap_components as dbc
from components.cards import make_card


def calc_fields_table_card() :
    return make_card("Pivot Table Calculated Fields", [
        html.Div(id="calculated-fields-container"),
        dbc.Button("➕ Add Field", id="add-calc-field-table", color="secondary", className="mt-2")
    ])

def calc_fields_chart_card() :
    return make_card("Chart Calculated Fields", [
        html.Div(id="calc-fields-chart-container"),
        dbc.Button("➕ Add Field", id="add-calc-field-chart", color="secondary", className="mt-2")
    ])

def rename_modal():
    return dbc.Modal([dbc.ModalHeader("Rename Column"),
        dbc.ModalBody(dbc.Input(id="rename-input", placeholder="Enter new column name", type="text", style={"width":"100%"})),
        dbc.ModalFooter([dbc.Button("Save", id="rename-save", color="primary"), dbc.Button("Cancel", id="rename-cancel", color="secondary", className="ms-2")])
    ], id="rename-modal", is_open=False, backdrop="static")