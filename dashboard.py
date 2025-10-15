import dash
from dash import html, dcc, Input, Output, State
import dash_pivottable
import pandas as pd
import numpy as np
import requests
import json
import re

# =======================
# STEP 1: Fetch Data
# =======================
def fetch_data():
    url = "http://127.0.0.1:8000/"
    response = requests.get(url, stream=True)
    records = []
    for line in response.iter_lines():
        if line:
            records.append(json.loads(line.decode("utf-8")))
    df_local = pd.DataFrame(records)
    df_local.columns = df_local.columns.str.strip()
    if "dpd_details_new" in df_local.columns:
        df_local["dpd_details_new"] = pd.to_numeric(df_local["dpd_details_new"], errors="coerce").fillna(0)
    return df_local

df = fetch_data()

# =======================
# STEP 2: Initialize App
# =======================
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# =======================
# STEP 3: Formula Parser
# =======================
def parse_formula(formula, dff):
    formula = formula.strip()
    cols = dff.columns.tolist()
    for col in cols:
        formula = re.sub(rf'\b{col}\b', f'dff["{col}"]', formula)

    if formula.lower().startswith("ifelse"):
        match = re.match(r"ifelse\((.*),(.*),(.*)\)", formula, re.IGNORECASE)
        if match:
            cond, true_val, false_val = [x.strip() for x in match.groups()]
            return np.where(
                pd.eval(cond, engine="python", target=dff),
                pd.eval(true_val, engine="python", target=dff),
                pd.eval(false_val, engine="python", target=dff)
            )
    return pd.eval(formula, engine="python", target=dff)

# =======================
# STEP 4: Layout
# =======================
app.layout = html.Div([
    html.H2("📊 Overdue Report Dashboard with Calculated Fields"),

    # Store for updated data
    dcc.Store(id="stored-data", data=df.to_dict("records")),

    # ---- Customer Filter ----
    html.Div([
        html.Label("Customer Type:"),
        dcc.Dropdown(
            id="customer_type",
            options=[{"label": s, "value": s} for s in sorted(df["customer_type"].dropna().unique())],
            value=None,
            multi=True,
            placeholder="Select customer_type"
        )
    ], style={"width": "50%", "margin": "20px"}),

    html.Hr(),

    # ---- Calculated Field ----
    html.Div([
        html.H3("Add Calculated Field"),
        html.Div([
            dcc.Input(
                id="calc-name",
                placeholder="Enter new field name",
                type="text",
                style={"width": "40%", "marginRight": "10px"}
            ),
            dcc.Input(
                id="calc-formula",
                placeholder='Formula (e.g., ifelse(dpd_details_new>0, loan_request_id, 0))',
                type="text",
                style={"width": "40%", "marginRight": "10px"}
            ),
            html.Button("Add Field", id="add-field-btn", n_clicks=0)
        ], style={"margin": "10px"}),
        html.Div(id="calc-status", style={"marginTop": "5px", "color": "green"})
    ], style={"margin": "20px"}),

    html.Hr(),

    # ---- Pivot Table Controls ----
    html.Div([
        html.Label("Rows:"),
        dcc.Dropdown(id="pivot-rows",
                     options=[{"label": c, "value": c} for c in df.columns],
                     value=["substate"],
                     multi=True,
                     placeholder="Select rows"),
        html.Label("Columns:"),
        dcc.Dropdown(id="pivot-cols",
                     options=[{"label": c, "value": c} for c in df.columns],
                     value=[],
                     multi=True,
                     placeholder="Select columns"),
        html.Label("Values:"),
        dcc.Dropdown(id="pivot-values",
                     options=[{"label": c, "value": c} for c in df.columns],
                     value=["loan_request_id"],
                     multi=True,
                     placeholder="Select value columns"),
        html.Label("Aggregator:"),
        dcc.Dropdown(
            id="pivot-aggregator",
            options=[
                {"label": "Count", "value": "Count"},
                {"label": "Sum", "value": "Sum"},
                {"label": "Average", "value": "Average"},
                {"label": "Max", "value": "Max"},
                {"label": "Min", "value": "Min"}
            ],
            value="Count"
        ),
        html.Label("Renderer:"),
        dcc.Dropdown(
            id="pivot-renderer",
            options=[
                {"label": "Table", "value": "Table"},
                {"label": "Heatmap", "value": "Heatmap"},
                {"label": "Bar Chart", "value": "Bar Chart"}
            ],
            value="Table"
        ),
    ], style={"width": "70%", "margin": "20px"}),

    # ---- Pivot Table ----
    html.Div([
        dash_pivottable.PivotTable(
            id="pivot-table",
            data=df.to_dict("records"),
            rows=["substate"],
            cols=[],
            vals=["loan_request_id"],
            aggregatorName="Count",
            rendererName="Table"
        )
    ], style={"margin": "20px"}),

    html.Hr()
])

# =======================
# STEP 5: Add Calculated Field
# =======================
@app.callback(
    Output("calc-status", "children"),
    Output("pivot-rows", "options"),
    Output("pivot-cols", "options"),
    Output("pivot-values", "options"),
    Output("stored-data", "data"),
    Input("add-field-btn", "n_clicks"),
    State("calc-name", "value"),
    State("calc-formula", "value"),
    prevent_initial_call=True
)
def add_calculated_field(n_clicks, field_name, formula):
    global df
    if not field_name or not formula:
        options = [{"label": c, "value": c} for c in df.columns]
        return "❌ Provide both name and formula.", options, options, options, df.to_dict("records")
    try:
        result = parse_formula(formula, df)
        # Convert NumPy array to Series before applying fillna
        df[field_name] = pd.to_numeric(pd.Series(result), errors="coerce").fillna(0)
        options = [{"label": c, "value": c} for c in df.columns]
        return f"✅ Added calculated field '{field_name}'", options, options, options, df.to_dict("records")
    except Exception as e:
        options = [{"label": c, "value": c} for c in df.columns]
        return f"❌ Error: {e}", options, options, options, df.to_dict("records")

# =======================
# STEP 6: Update Pivot Table
# =======================
@app.callback(
    Output("pivot-table", "data"),
    Output("pivot-table", "rows"),
    Output("pivot-table", "cols"),
    Output("pivot-table", "vals"),
    Output("pivot-table", "aggregatorName"),
    Output("pivot-table", "rendererName"),
    Input("pivot-rows", "value"),
    Input("pivot-cols", "value"),
    Input("pivot-values", "value"),
    Input("pivot-aggregator", "value"),
    Input("pivot-renderer", "value"),
    Input("customer_type", "value"),
    Input("stored-data", "data")
)
def update_pivot(rows, cols, vals, aggregator, renderer, selected_customer, stored_data):
    dff = pd.DataFrame(stored_data)
    if selected_customer:
        dff = dff[dff["customer_type"].isin(selected_customer)]
    if isinstance(vals, str):
        vals = [vals]
    return dff.to_dict("records"), rows, cols, vals, aggregator, renderer

# =======================
# STEP 7: Run App
# =======================
if __name__ == "__main__":
    app.run(debug=True, port=8050)