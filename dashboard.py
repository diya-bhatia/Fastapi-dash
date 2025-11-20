# dash_app.py
import dash
from dash import dcc, html, Input, Output, State, ALL, ctx, no_update, dash_table
import dash_bootstrap_components as dbc
import requests
import pandas as pd
import plotly.express as px
import time

API_BASE = "http://127.0.0.1:8000"
DATASETS_URL = f"{API_BASE}/api/datasets"
COLUMNS_URL = f"{API_BASE}/api/columns"
PIVOT_URL = f"{API_BASE}/api/pivot"

AGG_FUNCS = ["sum", "mean", "count", "max", "min"]

# ---------- App init ----------
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="📊 FastAPI + Dash Analytics"
)

# ---------- Helpers ----------
def post_df(url, payload):
    try:
        res = requests.post(url, json=payload, timeout=30)
        if not res.ok:
            try:
                detail = res.json().get("detail", res.text)
            except Exception:
                detail = res.text
            return None, f"{res.status_code}: {detail}"
        return pd.DataFrame(res.json()), None
    except Exception as e:
        return None, f"Request failed: {e}"

def get_json(url):
    try:
        res = requests.get(url, timeout=30)
        if not res.ok:
            try:
                detail = res.json().get("detail", res.text)
            except Exception:
                detail = res.text
            return None, f"{res.status_code}: {detail}"
        return res.json(), None
    except Exception as e:
        return None, f"Request failed: {e}"
# ---------- Layout pieces ----------

# Sidebar (dark)
left_panel = dbc.Card(
    [
        dbc.CardHeader(html.H5("🧭 Datasets", className="text-white")),
        dbc.CardBody(
            [
                dbc.Button("➕ Add Dataset", id="open-dataset-modal", color="light", outline=True, className="mb-3 w-100", n_clicks=0),
                dbc.Modal(
                    [
                        dbc.ModalHeader(dbc.ModalTitle("Add Dataset")),
                        dbc.ModalBody(
                            [
                                dbc.Input(id="ds-name", placeholder="Dataset name", className="mb-2"),
                                dcc.Dropdown(
                                    id="ds-source-type",
                                    options=[{"label": "S3", "value": "s3"}, {"label": "Local file", "value": "local"}],
                                    value="s3",
                                    className="mb-2"
                                ),
                                dcc.Dropdown(
                                    id="ds-file-format",
                                    options=[{"label": "Parquet", "value": "parquet"}, {"label": "CSV", "value": "csv"}],
                                    value="parquet",
                                    className="mb-2"
                                ),
                                html.Div(
                                    [
                                        html.Div([
                                            dbc.Input(id="ds-s3-bucket", placeholder="S3 bucket", className="mb-2"),
                                            dbc.Input(id="ds-s3-key", placeholder="S3 key (prefix or key)", className="mb-2"),
                                        ], id="s3-fields"),
                                        html.Div([
                                            dbc.Input(id="ds-local-path", placeholder="Local file path", className="mb-2"),
                                        ], id="local-fields")
                                    ], id="ds-source-fields"
                                )
                            ]
                        ),
                        dbc.ModalFooter(
                            [
                                dbc.Button("Cancel", id="ds-cancel", className="me-2", n_clicks=0),
                                dbc.Button("Add", id="ds-add", color="primary", n_clicks=0)
                            ]
                        )
                    ],
                    id="dataset-modal",
                    is_open=False
                ),
                html.Div(id="datasets-list", className="mt-2 text-white")
            ]
        ),
    ],
    style={"backgroundColor": "#2F3E46", "height": "100vh", "border": "none"}
)

# Workspace cards (lighter, subtle shadows)
def make_card(title, children):
    return dbc.Card(
        [
            dbc.CardHeader(html.H5(title, className="fw-bold")),
            dbc.CardBody(children)
        ],
        className="mb-3 shadow-sm",
        style={"backgroundColor": "#F8F9FA", "borderRadius": "8px"}
    )

calc_fields_table = make_card("Pivot Table Calculated Fields", [
    html.Div(id="calculated-fields-container", children=[]),
    dbc.Button("➕ Add Field", id="add-calc-field-table", color="secondary", className="mt-2")
])

calc_fields_chart = make_card("Chart Calculated Fields", [
    html.Div(id="calc-fields-chart-container", children=[]),
    dbc.Button("➕ Add Field", id="add-calc-field-chart", color="secondary", className="mt-2")
])

workspace = dbc.Container(
    [
        # Stores
        dcc.Store(id="columns_store", data=[]),
        dcc.Store(id="datasets_refresh_store", data=0),
        dcc.Store(id="calculated_fields_store", data=[]),
        dcc.Store(id="calculated_fields_chart_store", data=[]),

        dbc.Row(
            [
                dbc.Col(
                    make_card("Pivot Table Settings", [
                        html.Label("Dataset:"), dcc.Dropdown(id="table-dataset", options=[], placeholder="Select dataset", className="mb-2"),
                        html.Label("Rows:"), dcc.Dropdown(id="table-rows", multi=True, options=[]),
                        html.Label("Columns:"), dcc.Dropdown(id="table-cols", multi=True, options=[]),
                        html.Label("Values:"), dcc.Dropdown(id="table-vals", multi=True, options=[]),
                        html.Label("Aggregation:"), dcc.Dropdown(id="table-aggfunc", options=[{"label": a, "value": a} for a in AGG_FUNCS], value=AGG_FUNCS[0]),
                        calc_fields_table,
                        dbc.Button("Generate Table", id="generate-table", color="primary", className="mt-3 w-100", n_clicks=0)
                    ]),
                    width=5
                ),
                dbc.Col(
                    make_card("Chart Settings", [
                        html.Label("Dataset:"), dcc.Dropdown(id="chart-dataset", options=[], placeholder="Select dataset", className="mb-2"),
                        html.Label("X-axis:"), dcc.Dropdown(id="chart-rows", multi=False, options=[]),
                        html.Label("Values:"), dcc.Dropdown(id="chart-vals", multi=True, options=[]),
                        html.Label("Aggregation:"), dcc.Dropdown(id="chart-aggfunc", options=[{"label": a, "value": a} for a in AGG_FUNCS], value=AGG_FUNCS[0]),
                        calc_fields_chart,
                        dbc.Button("Generate Chart", id="generate-chart", color="success", className="mt-3 w-100", n_clicks=0)
                    ]),
                    width=7
                ),
            ],
            className="mb-3"
        ),
        dbc.Row(dbc.Col(make_card("Pivot Table", dbc.Spinner(html.Div(id="pivot-table"))), width=12)),
        dbc.Row(dbc.Col(make_card("Chart", dcc.Graph(id="pivot-chart")), width=12))
    ],
    fluid=True,
    style={"padding": "20px", "backgroundColor": "#E5E5E5"}
)

# App layout
app.layout = dbc.Container([dbc.Row([dbc.Col(left_panel, width=3), dbc.Col(workspace, width=9)])], fluid=True)

# ---------- Chart theme ----------
px.defaults.template = "plotly_white"
px.defaults.color_continuous_scale = px.colors.sequential.Viridis


# ---------- Callbacks: dataset management (unchanged logic) ----------
@app.callback(
    Output("dataset-modal", "is_open"),
    Input("open-dataset-modal", "n_clicks"),
    Input("ds-cancel", "n_clicks"),
    Input("ds-add", "n_clicks"),
    State("dataset-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_dataset_modal(open_click, cancel_click, add_click, is_open):
    trig = ctx.triggered_id
    if trig == "open-dataset-modal":
        return True
    if trig in ("ds-cancel", "ds-add"):
        return False
    return is_open

@app.callback(
    Output("s3-fields", "style"),
    Output("local-fields", "style"),
    Input("ds-source-type", "value")
)
def toggle_source_fields(source_type):
    if source_type == "s3":
        return {"display": "block"}, {"display": "none"}
    return {"display": "none"}, {"display": "block"}

def render_datasets(datasets):
    if not datasets:
        return html.Div("No datasets yet.", className="text-muted")
    items = []
    for d in datasets:
        items.append(dbc.ListGroupItem([
            html.Div([html.Strong(d.get("name", d.get("id"))), html.Span(f" • {d.get('source_type','?')}/{d.get('file_format','?')}", className="text-muted ms-2")]),
            dbc.Button("Use", id={"type": "use-dataset", "id": d["id"]}, size="sm", className="mt-2")
        ]))
    return dbc.ListGroup(items)

@app.callback(
    Output("datasets-list", "children"),
    Input("datasets_refresh_store", "data")
)
def load_datasets(_):
    datasets, err = get_json(DATASETS_URL)
    if err:
        return html.Div(f"Failed to load datasets: {err}", className="text-danger")
    return render_datasets(datasets or [])

@app.callback(
    Output("datasets_refresh_store", "data"),
    Input("ds-add", "n_clicks"),
    State("ds-name", "value"),
    State("ds-source-type", "value"),
    State("ds-file-format", "value"),
    State("ds-s3-bucket", "value"),
    State("ds-s3-key", "value"),
    State("ds-local-path", "value"),
    State("datasets_refresh_store", "data"),
    prevent_initial_call=True
)
def add_dataset(n_clicks, name, source_type, file_format, s3_bucket, s3_key, local_path, refresh_counter):
    payload = {"name": name or "", "source_type": source_type, "file_format": file_format}
    if source_type == "s3":
        payload["s3"] = {"bucket": (s3_bucket or "").strip(), "key": (s3_key or "").strip()}
    elif source_type == "local":
        payload["local_path"] = (local_path or "").strip()
    try:
        res = requests.post(DATASETS_URL, json=payload, timeout=30)
        res.raise_for_status()
        ds_id = res.json().get("id")
        if ds_id:
            try:
                act = requests.post(f"{API_BASE}/api/activate_dataset/{ds_id}", timeout=10)
                act.raise_for_status()
            except Exception as e:
                print("Warning: failed to activate dataset:", e)
    except Exception as e:
        print("Error adding dataset:", e)
    return (refresh_counter or 0) + 1

@app.callback(
    Output("table-dataset", "value"),
    Output("chart-dataset", "value"),
    Input({"type": "use-dataset", "id": ALL}, "n_clicks"),
    State({"type": "use-dataset", "id": ALL}, "id"),
    prevent_initial_call=True
)
def use_dataset(n_clicks_list, ids):
    if not n_clicks_list or not any(n_clicks_list):
        return no_update, no_update
    idx = n_clicks_list.index(max(n_clicks_list))
    dataset_id = ids[idx]["id"]
    try:
        res = requests.post(f"{API_BASE}/api/activate_dataset/{dataset_id}", timeout=10)
        res.raise_for_status()
    except Exception as e:
        print("Failed to activate dataset:", e)
    return dataset_id, dataset_id

@app.callback(
    Output("table-dataset", "options"),
    Output("chart-dataset", "options"),
    Input("datasets_refresh_store", "data")
)
def update_dataset_options(_):
    datasets, err = get_json(DATASETS_URL)
    if err:
        return [], []
    options = [{"label": d.get("name", d.get("id")), "value": d["id"]} for d in (datasets or [])]
    return options, options

@app.callback(
    Output("columns_store", "data"),
    Input("table-dataset", "value"),
    Input("chart-dataset", "value")
)
def fetch_columns(table_ds, chart_ds):
    dataset_id = table_ds or chart_ds
    if not dataset_id:
        return []
    data, err = get_json(f"{COLUMNS_URL}?dataset_id={dataset_id}")
    if err:
        print("Failed to fetch columns:", err)
        return []
    if isinstance(data, dict) and "columns" in data:
        return data["columns"]
    if isinstance(data, list):
        return data
    return []

# ---------- Calculated fields: add editable rows ----------
@app.callback(
    Output("calculated-fields-container", "children"),
    Output("calc-fields-chart-container", "children"),
    Input("add-calc-field-table", "n_clicks"),
    Input("add-calc-field-chart", "n_clicks"),
    State("calculated-fields-container", "children"),
    State("calc-fields-chart-container", "children"),
    prevent_initial_call=True
)
def update_calc_fields(add_table_clicks, add_chart_clicks, table_children, chart_children):
    table_children = table_children or []
    chart_children = chart_children or []

    trig = ctx.triggered_id
    ts = str(time.time()).replace('.', '')
    short_ts = ts[-8:]

    if trig == "add-calc-field-table":
        default_name = f"calc_{short_ts}"
        # id on inputs themselves and on save button (pattern-matching)
        row = dbc.Row([
            dbc.Col(dbc.Input(id={"type": "calc-name", "index": ts}, placeholder="Field name", type="text", value=default_name), width=4),
            dbc.Col(dbc.Input(id={"type": "calc-formula", "index": ts}, placeholder="Formula", type="text", value=""), width=6),
            dbc.Col(dbc.Button("Save", id={"type": "save-calc", "index": ts}, color="primary", n_clicks=0), width=2)
        ], className="mb-1", id={"type": "calc-row", "index": ts})
        table_children.append(row)

    elif trig == "add-calc-field-chart":
        default_name = f"calcc_{short_ts}"
        row = dbc.Row([
            dbc.Col(dbc.Input(id={"type": "calc-name-chart", "index": ts}, placeholder="Field name", type="text", value=default_name), width=4),
            dbc.Col(dbc.Input(id={"type": "calc-formula-chart", "index": ts}, placeholder="Formula", type="text", value=""), width=6),
            dbc.Col(dbc.Button("Save", id={"type": "save-calc-chart", "index": ts}, color="primary", n_clicks=0), width=2)
        ], className="mb-1", id={"type": "calc-row-chart", "index": ts})
        chart_children.append(row)

    return table_children, chart_children

# ---------- Save callback: table-calculated fields ----------
@app.callback(
    Output("calculated_fields_store", "data"),
    Input({"type": "save-calc", "index": ALL}, "n_clicks"),
    State({"type": "save-calc", "index": ALL}, "id"),
    State({"type": "calc-name", "index": ALL}, "id"),
    State({"type": "calc-name", "index": ALL}, "value"),
    State({"type": "calc-formula", "index": ALL}, "id"),
    State({"type": "calc-formula", "index": ALL}, "value"),
    State("calculated_fields_store", "data"),
    prevent_initial_call=True
)
def save_calc_field(n_clicks_list, save_btn_ids, name_ids, all_names, formula_ids, all_formulas, store):
    """
    When any Save button is clicked in table-calculated rows,
    find the matching name/formula by matching the 'index' in their id dicts,
    and append to the store if valid and not duplicate.
    """
    if not n_clicks_list or not any(n_clicks_list):
        return store or []

    store = store or []

    # which Save button was clicked (the one with max n_clicks)
    idx = n_clicks_list.index(max(n_clicks_list))
    target_index = save_btn_ids[idx]["index"]

    # find position in the name_ids list that has same index
    pos = None
    for i, id_dict in enumerate(name_ids or []):
        if id_dict and id_dict.get("index") == target_index:
            pos = i
            break

    # fallback if not found
    if pos is None:
        pos = idx if idx < len(all_names or []) else None
    if pos is None:
        return store

    name = (all_names or [])[pos]
    formula = (all_formulas or [])[pos]

    # validate
    if not name or not formula:
        return store

    # prevent duplicate names
    if any(f.get("name") == name for f in store):
        return store

    store.append({"name": name, "formula": formula})
    return store

# ---------- Save callback: chart-calculated fields ----------
@app.callback(
    Output("calculated_fields_chart_store", "data"),
    Input({"type": "save-calc-chart", "index": ALL}, "n_clicks"),
    State({"type": "save-calc-chart", "index": ALL}, "id"),
    State({"type": "calc-name-chart", "index": ALL}, "id"),
    State({"type": "calc-name-chart", "index": ALL}, "value"),
    State({"type": "calc-formula-chart", "index": ALL}, "id"),
    State({"type": "calc-formula-chart", "index": ALL}, "value"),
    State("calculated_fields_chart_store", "data"),
    prevent_initial_call=True
)
def save_calc_field_chart(n_clicks_list, save_btn_ids, name_ids, all_names, formula_ids, all_formulas, store):
    if not n_clicks_list or not any(n_clicks_list):
        return store or []
    store = store or []

    idx = n_clicks_list.index(max(n_clicks_list))
    target_index = save_btn_ids[idx]["index"]

    pos = None
    for i, id_dict in enumerate(name_ids or []):
        if id_dict and id_dict.get("index") == target_index:
            pos = i
            break
    if pos is None:
        pos = idx if idx < len(all_names or []) else None
    if pos is None:
        return store

    name = (all_names or [])[pos]
    formula = (all_formulas or [])[pos]
    if not name or not formula:
        return store
    if any(f.get("name") == name for f in store):
        return store
    store.append({"name": name, "formula": formula})
    return store

# ---------- Populate dropdowns using real committed calculated fields ----------
@app.callback(
    Output("table-rows", "options"),
    Output("table-cols", "options"),
    Output("table-vals", "options"),
    Output("chart-rows", "options"),
    Output("chart-vals", "options"),
    Input("columns_store", "data"),
    Input("calculated_fields_store", "data"),
    Input("calculated_fields_chart_store", "data"),
)
def populate_dropdowns(columns, calc_store, calc_store_chart):
    calc_names = [f["name"] for f in (calc_store or [])]
    calc_names_chart = [f["name"] for f in (calc_store_chart or [])]

    def make_options(base_cols, extra_names):
        seen = set()
        opts = []
        for c in (base_cols or []) + extra_names:
            if c not in seen:
                seen.add(c)
                opts.append({"label": c, "value": c})
        return opts

    all_table_options = make_options(columns, calc_names)
    all_chart_options = make_options(columns, calc_names_chart)

    return all_table_options, all_table_options, all_table_options, all_chart_options, all_chart_options

# ---------- Auto-select new committed calculated fields into Values ----------
@app.callback(
    Output("table-vals", "value"),
    Input("calculated_fields_store", "data"),
    State("table-vals", "value"),
)
def auto_select_calc_fields(calc_store, current_vals):
    calc_names = [f["name"] for f in (calc_store or [])]
    current_vals = current_vals or []
    for c in calc_names:
        if c not in current_vals:
            current_vals.append(c)
    return current_vals

@app.callback(
    Output("chart-vals", "value"),
    Input("calculated_fields_chart_store", "data"),
    State("chart-vals", "value"),
)
def auto_select_calc_fields_chart(calc_store, current_vals):
    calc_names = [f["name"] for f in (calc_store or [])]
    current_vals = current_vals or []
    for c in calc_names:
        if c not in current_vals:
            current_vals.append(c)
    return current_vals



@app.callback(
    Output("pivot-table", "children"),
    Input("generate-table", "n_clicks"),
    State("table-dataset", "value"),
    State("table-rows", "value"),
    State("table-cols", "value"),
    State("table-vals", "value"),
    State("table-aggfunc", "value"),
    State("calculated_fields_store", "data"),
    prevent_initial_call=True
)
def generate_table(n, ds, rows, cols, vals, aggfunc, calc_store):
    if not ds:
        return html.Div("Select a dataset first.", className="text-warning")

    calculated_fields = [{"name": f["name"], "formula": f["formula"]} for f in (calc_store or [])]
    payload = {
        "dataset_id": ds,
        "rows": rows or [],
        "columns": cols or [],
        "values": vals or [],
        "aggfunc": aggfunc,
        "calculated_fields": calculated_fields
    }

    df, err = post_df(PIVOT_URL, payload)
    if err or df is None or df.empty:
        return html.Div(f"No data found. {err or ''}", className="text-muted")

    # ---- Header style ----
    header_style = {
        "backgroundColor": "#670178",  # purple
        "color": "white",
        "fontWeight": "bold",
        "textAlign": "center",
        "padding": "8px",
        "borderBottom": "2px solid #555",
        "borderRight": "1px solid #bbb",
        "position": "sticky",
        "top": "0",
        "zIndex": "3"  # higher than total row
    }

    # ---- Row style function ----
    def get_row_style(idx, row, is_first_col=False):
        style = {
            "textAlign": "center",
            "padding": "6px",
            "whiteSpace": "nowrap",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "borderRight": "1px solid #bbb",   # vertical line
            "borderBottom": "1px solid #bbb",  # horizontal line
            "backgroundColor": "white",
        }
        if is_first_col:
            style.update({
                "position": "sticky",
                "left": "0",
                "backgroundColor": "white",
                "zIndex": "2"
            })
        return style

    # ---- Table header ----
    table_header = html.Tr([
        html.Th(df.columns[0], style={**header_style, "left": "0", "zIndex": "4"}),  # sticky first column header
        *[html.Th(col, style=header_style) for col in df.columns[1:]]
    ])

    # ---- Table body ----
    table_rows = []
    total_row = None
    for i, row in df.iterrows():
        first_col_val = str(row.iloc[0]).lower()
        is_total = "total" in first_col_val
        tds = []
        for j, c in enumerate(df.columns):
            is_first_col = j == 0
            td_style = get_row_style(i, row, is_first_col=is_first_col)
            if is_total:
                td_style.update({
                    "backgroundColor": "#670178",  # purple total row
                    "color": "white",
                    "fontWeight": "bold",
                    "zIndex": "1",
                    "position": "sticky" if is_first_col else td_style.get("position", "static"),
                    "left": "0" if is_first_col else td_style.get("left", "auto"),
                    "borderBottom": "1px solid #555"  # horizontal line for total
                })
            tds.append(html.Td(row[c], style=td_style))
        tr = html.Tr(tds)
        if is_total:
            total_row = tr
        else:
            table_rows.append(tr)

    if total_row:
        table_rows.append(total_row)

    table_style = {
        "width": "100%",
        "borderCollapse": "collapse",
        "tableLayout": "fixed",
        "fontFamily": "Arial, sans-serif",
        "fontSize": "14px"
    }

    container_style = {
        "overflowX": "auto",  # horizontal scroll
        "maxHeight": "100%",
        "border": "1px solid #ccc",
        "borderRadius": "6px"
    }

    return html.Div(
        html.Table([html.Thead(table_header), html.Tbody(table_rows)], style=table_style),
        style=container_style,
        className="pivot-table-container"
    )


# ---------- Generate Chart (payload includes committed chart-calculated fields) ----------
@app.callback(
    Output("pivot-chart", "figure"),
    Input("generate-chart", "n_clicks"),
    State("chart-dataset", "value"),
    State("chart-rows", "value"),
    State("chart-vals", "value"),
    State("chart-aggfunc", "value"),
    State("calculated_fields_chart_store", "data"),
    prevent_initial_call=True
)
def generate_chart(n, ds, x_col, vals, aggfunc, calc_store):
    if not ds or not x_col:
        return {}
    calculated_fields = [{"name": f["name"], "formula": f["formula"]} for f in (calc_store or [])]
    payload = {"dataset_id": ds, "rows": [x_col], "columns": [], "values": vals or [], "aggfunc": aggfunc, "calculated_fields": calculated_fields}
    df, err = post_df(PIVOT_URL, payload)
    if err or df is None or df.empty:
        return {}
    y_cols = vals if vals else [c for c in df.columns if c != x_col]
    fig = px.bar(df, x=x_col, y=y_cols, barmode="group")
    return fig

if __name__ == "__main__":
    app.run(debug=True, port=8050)
