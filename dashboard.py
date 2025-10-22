import dash
from dash import dcc, html, Input, Output, State, ALL, ctx, no_update
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

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="📊 FastAPI + Dash Analytics"
)

# =========================
# Helpers
# =========================
def post_df(url, payload):
    try:
        res = requests.post(url, json=payload, timeout=30)
        if not res.ok:
            detail = res.json().get("detail", res.text)
            return None, f"{res.status_code}: {detail}"
        return pd.DataFrame(res.json()), None
    except Exception as e:
        return None, f"Request failed: {e}"

def get_json(url):
    try:
        res = requests.get(url, timeout=30)
        if not res.ok:
            detail = res.json().get("detail", res.text)
            return None, f"{res.status_code}: {detail}"
        return res.json(), None
    except Exception as e:
        return None, f"Request failed: {e}"

def current_ts():
    return time.time()

def alert_payload(message, open=True):
    return {"open": open, "message": message, "ts": current_ts()}

# =========================
# Layout
# =========================
left_panel = dbc.Card([
    dbc.CardHeader(html.H5("🧭 Datasets")),
    dbc.CardBody([
        dbc.Button("➕ Add Dataset", id="open-dataset-modal", color="secondary", outline=True, className="mb-2"),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Add Dataset")),
            dbc.ModalBody([
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
                html.Div(id="ds-source-fields")
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="ds-cancel", className="me-2"),
                dbc.Button("Add", id="ds-add", color="primary")
            ])
        ], id="dataset-modal", is_open=False),
        html.Div(id="datasets-list", className="mt-2")
    ])
])

workspace = dbc.Container([
    dcc.Store(id="columns_store", data=[]),
    dcc.Store(id="datasets_refresh_store", data=0),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Pivot Table Settings")),
                dbc.CardBody([
                    html.Label("Dataset:"),
                    dcc.Dropdown(id="table-dataset", options=[], placeholder="Select dataset", className="mb-2"),
                    html.Label("Rows:"), dcc.Dropdown(id="table-rows", multi=True, options=[]),
                    html.Label("Columns:"), dcc.Dropdown(id="table-cols", multi=True, options=[]),
                    html.Label("Values:"), dcc.Dropdown(id="table-vals", multi=True, options=[]),
                    html.Label("Aggregation:"), 
                    dcc.Dropdown(id="table-aggfunc", options=[{"label": a, "value": a} for a in AGG_FUNCS], value=AGG_FUNCS[0]),
                    dbc.Button("Generate Table", id="generate-table", color="primary", className="mt-3 w-100")
                ])
            ])
        ], width=5),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Chart Settings")),
                dbc.CardBody([
                    html.Label("Dataset:"), dcc.Dropdown(id="chart-dataset", options=[], placeholder="Select dataset", className="mb-2"),
                    html.Label("X-axis:"), dcc.Dropdown(id="chart-rows", multi=False, options=[]),
                    html.Label("Values:"), dcc.Dropdown(id="chart-vals", multi=True, options=[]),
                    html.Label("Aggregation:"), 
                    dcc.Dropdown(id="chart-aggfunc", options=[{"label": a, "value": a} for a in AGG_FUNCS], value=AGG_FUNCS[0]),
                    dbc.Button("Generate Chart", id="generate-chart", color="success", className="mt-3 w-100")
                ])
            ])
        ], width=7)
    ]),

    dbc.Row([
        dbc.Col(dbc.Card([dbc.CardHeader(html.H5("Pivot Table")), dbc.CardBody(dbc.Spinner(html.Div(id="pivot-table")))]), width=12)
    ]),

    dbc.Row([
        dbc.Col(dbc.Card([dbc.CardHeader(html.H5("Chart")), dbc.CardBody(dbc.Spinner(dcc.Graph(id="pivot-chart")))]), width=12)
    ])
], fluid=True)

app.layout = dbc.Container([
    dbc.Row([dbc.Col(left_panel, width=3), dbc.Col(workspace, width=9)])
], fluid=True)

# =========================
# Dataset Modal
# =========================
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
    if trig == "open-dataset-modal": return True
    if trig in ("ds-cancel", "ds-add"): return False
    return is_open

@app.callback(
    Output("ds-source-fields", "children"),
    Input("ds-source-type", "value"),
    Input("ds-file-format", "value")
)
def render_source_fields(source_type, fmt):
    if source_type == "s3":
        return html.Div([
            dbc.Input(id="ds-s3-bucket", placeholder="S3 bucket", className="mb-2"),
            dbc.Input(id="ds-s3-key", placeholder="S3 key", className="mb-2"),
        ])
    return html.Div([dbc.Input(id="ds-local-path", placeholder="Local file path", className="mb-2")])

# =========================
# Load Datasets & Use Button
# =========================
def render_datasets(datasets):
    if not datasets: return html.Div("No datasets yet.", className="text-muted")
    items = []
    for d in datasets:
        items.append(dbc.ListGroupItem([
            html.Div([html.Strong(d["name"]), html.Span(f"  •  {d['source_type']}/{d['file_format']}", className="text-muted ms-2")]),
            dbc.Button("Use", id={"type": "use-dataset", "id": d["id"]}, size="sm", className="mt-2")
        ]))
    return dbc.ListGroup(items)

@app.callback(
    Output("datasets-list", "children"),
    Input("datasets_refresh_store", "data")
)
def load_datasets(_):
    datasets, err = get_json(DATASETS_URL)
    if err: return html.Div(f"Failed to load datasets: {err}", className="text-danger")
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
def add_dataset(_, name, source_type, file_format, s3_bucket, s3_key, local_path, refresh_counter):
    payload = {"name": name or "", "source_type": source_type, "file_format": file_format}
    if source_type == "s3": payload["s3"] = {"bucket": s3_bucket or "", "key": s3_key or ""}
    else: payload["local"] = {"path": local_path or ""}
    res, err = requests.post(DATASETS_URL, json=payload), None
    return (refresh_counter or 0) + 1, 

@app.callback(
    Output("table-dataset", "value"),
    Output("chart-dataset", "value"),
    Input({"type": "use-dataset", "id": ALL}, "n_clicks"),
    State({"type": "use-dataset", "id": ALL}, "id"),
    prevent_initial_call=True
)
def use_dataset(n_clicks_list, ids):
    if not n_clicks_list or not any(n_clicks_list): return no_update, no_update
    idx = n_clicks_list.index(max(n_clicks_list))
    dataset_id = ids[idx]["id"]
    return dataset_id, dataset_id

@app.callback(
    Output("table-dataset", "options"),
    Output("chart-dataset", "options"),
    Input("datasets_refresh_store", "data")
)
def update_dataset_options(_):
    datasets, err = get_json(DATASETS_URL)
    if err: return [], []
    options = [{"label": d["name"], "value": d["id"]} for d in (datasets or [])]
    return options, options

# =========================
# Fetch Columns & Populate Dropdowns
# =========================
@app.callback(
    Output("columns_store", "data"),
    Input("table-dataset", "value"),
    Input("chart-dataset", "value")
)
def fetch_columns(table_ds, chart_ds):
    dataset_id = table_ds or chart_ds
    if not dataset_id: return []
    data, err = get_json(f"{COLUMNS_URL}?dataset_id={dataset_id}")
    if err: return []
    if isinstance(data, dict) and "columns" in data: return data["columns"]
    if isinstance(data, list): return data
    return []

@app.callback(
    Output("table-rows", "options"),
    Output("table-cols", "options"),
    Output("table-vals", "options"),
    Output("chart-rows", "options"),
    Output("chart-vals", "options"),
    Input("columns_store", "data")
)
def populate_dropdowns(columns):
    if not columns: return [], [], [], [], []
    options = [{"label": c, "value": c} for c in columns]
    return options, options, options, options, options

# =========================
# Pivot Table & Chart
# =========================
@app.callback(
    Output("pivot-table", "children"),
    Input("generate-table", "n_clicks"),
    State("table-dataset", "value"),
    State("table-rows", "value"),
    State("table-cols", "value"),
    State("table-vals", "value"),
    State("table-aggfunc", "value"),
    prevent_initial_call=True
)
def generate_table(n, ds, rows, cols, vals, aggfunc):
    if not ds: return "", None
    payload = {"dataset_id": ds, "index": rows or [], "columns": cols or [], "values": vals or [], "aggfunc": aggfunc}
    df, err = post_df(PIVOT_URL, payload)
    if err or df is None or df.empty: return html.Div("No data found.", className="text-muted"), None
    return dbc.Table.from_dataframe(df, striped=True, bordered=True, hover=True), None

@app.callback(
    Output("pivot-chart", "figure"),
    Input("generate-chart", "n_clicks"),
    State("chart-dataset", "value"),
    State("chart-rows", "value"),
    State("chart-vals", "value"),
    State("chart-aggfunc", "value"),
    prevent_initial_call=True
)
def generate_chart(n, ds, x_col, vals, aggfunc):
    if not ds or not x_col: return {}, None
    payload = {"dataset_id": ds, "index": [x_col], "values": vals or [], "aggfunc": aggfunc}
    df, err = post_df(PIVOT_URL, payload)
    if err or df is None or df.empty: return {}, None
    y_cols = vals if vals else [c for c in df.columns if c != x_col]
    fig = px.bar(df, x=x_col, y=y_cols, barmode="group")
    return fig, None

# =========================
if __name__ == "__main__":
    app.run(debug=True, port=8050)
