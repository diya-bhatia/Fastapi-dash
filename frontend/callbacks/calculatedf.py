from dash import ctx, Input, Output, State, ALL
import dash_bootstrap_components as dbc
from dash import html
import time

def register_calculated_fields_callbacks(app):

    # --- Add dynamic calculated field rows ---
    @app.callback(
        Output("calculated-fields-container","children"),
        Input("add-calc-field-table","n_clicks"),
        State("calculated-fields-container","children"),
        prevent_initial_call=True
    )
    def update_calc_fields(add_table_clicks, table_children):
        table_children = table_children or []
        trig = ctx.triggered_id
        ts = str(time.time()).replace('.', '')
        short_ts = ts[-8:]

        if trig == "add-calc-field-table":
            default_name = f"calc_{short_ts}"
            row = dbc.Row([
                dbc.Col(dbc.Input(id={"type":"calc-name","index":ts}, value=default_name), width=4),
                dbc.Col(dbc.Input(id={"type":"calc-formula","index":ts}), width=6),
                dbc.Col(dbc.Button("Save", id={"type":"save-calc","index":ts}), width=2)
            ], className="mb-2")
            table_children.append(row)

        return table_children


    # --- Save calculated field to store ---
    @app.callback(
        Output("calculated_fields_store", "data"),
        Input({"type":"save-calc","index":ALL}, "n_clicks"),
        State({"type":"calc-name","index":ALL}, "value"),
        State({"type":"calc-formula","index":ALL}, "value"),
        State("calculated_fields_store", "data"),
        prevent_initial_call=True
    )
    def save_calc_field(n_clicks, names, formulas, store):
        store = store or []

        trig_id = ctx.triggered_id
        if not trig_id:
            return store

        # Find index of the clicked Save button
        try:
            idx = next(i for i, n in enumerate(n_clicks) 
                       if n and trig_id["index"] == ctx.inputs_list[0][i]["id"]["index"])
        except StopIteration:
            return store

        name = names[idx]
        formula = formulas[idx]

        # Add only if not duplicate
        if name and formula and not any(f["name"] == name for f in store):
            store.append({"name": name, "formula": formula})

        return store
