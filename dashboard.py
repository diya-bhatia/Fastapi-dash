import dash
from dash import dcc, html, Input, Output, State, ALL, ctx, no_update
import dash_bootstrap_components as dbc
import requests
import pandas as pd
import plotly.express as px
import json
import time

API_BASE = "http://127.0.0.1:8000"
DATASETS_URL = f"{API_BASE}/api/datasets"
COLUMNS_URL = f"{API_BASE}/api/columns"
PIVOT_URL = f"{API_BASE}/api/pivot"
DISTINCT_URL = f"{API_BASE}/api/distinct"
REPORTS_URL = f"{API_BASE}/api/reports"

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
            try:
                detail = res.json().get("detail")
            except Exception:
                detail = res.text
            return None, f"{res.status_code}: {detail}"
        return pd.DataFrame(res.json()), None
    except Exception as e:
        return None, f"Request failed: {e}"

def post_json(url, payload):
    try:
        res = requests.post(url, json=payload, timeout=30)
        if not res.ok:
            try:
                detail = res.json().get("detail")
            except Exception:
                detail = res.text
            return None, f"{res.status_code}: {detail}"
        return res.json(), None
    except Exception as e:
        return None, f"Request failed: {e}"

def get_json(url):
    try:
        res = requests.get(url, timeout=30)
        if not res.ok:
            try:
                detail = res.json().get("detail")
            except Exception:
                detail = res.text
            return None, f"{res.status_code}: {detail}"
        return res.json(), None
    except Exception as e:
        return None, f"Request failed: {e}"

def current_ts():
    return time.time()

def collect_calculated_fields(names, formulas):
    calcs = {}
    if names and formulas:
        for n, f in zip(names, formulas):
            if (n or "").strip() and (f or "").strip():
                calcs[n.strip()] = f.strip()
    return calcs

def alert_payload(message, open=True):
    return {"open": open, "message": message, "ts": current_ts()}

# =========================
# Layout
# =========================
dataset_modal = dbc.Modal([
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
], id="dataset-modal", is_open=False)

left_panel = dbc.Card([
    dbc.CardHeader(html.H5("🧭 Datasets & Reports")),
    dbc.CardBody([
        html.H6("Datasets"),
        dbc.Button("➕ Add Dataset", id="open-dataset-modal", color="secondary", outline=True, className="mb-2"),
        dataset_modal,
        html.Div(id="datasets-list", className="mb-3"),
        html.Hr(),
        html.H6("Reports"),
        dbc.Button("💾 Save Report", id="save-report", color="primary", outline=True, className="mb-2"),
        html.Div(id="reports-list", className="mb-3"),
        dbc.Alert(id="left-alert", is_open=False, color="info"),
    ])
])

workspace = dbc.Container([
    # Stores
    dcc.Store(id="dataset_store", data=None),            # active dataset_id
    dcc.Store(id="columns_store", data=[]),              # dataset columns
    dcc.Store(id="calc_rows", data=[]),
    dcc.Store(id="filter_rows", data=[]),
    dcc.Store(id="calculated_fields_store", data={}),    # canonical calcs
    dcc.Store(id="alert_table_store", data=None),
    dcc.Store(id="alert_chart_store", data=None),
    dcc.Store(id="reports_store", data=[]),
    dcc.Store(id="active_report_store", data=None),

    # Left-panel alert stores
    dcc.Store(id="left_alert_dataset_store", data=None),
    dcc.Store(id="left_alert_reports_store", data=None),

    # Refresh triggers (single writers for lists)
    dcc.Store(id="datasets_refresh_store", data=0),
    dcc.Store(id="reports_refresh_store", data=0),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Pivot Table Settings")),
                dbc.CardBody([
                    html.Label("Rows:"),
                    dcc.Dropdown(id="table-rows", multi=True, options=[]),

                    html.Label("Columns:", className="mt-2"),
                    dcc.Dropdown(id="table-cols", multi=True, options=[]),

                    html.Label("Values:", className="mt-2"),
                    dcc.Dropdown(id="table-vals", multi=True, options=[]),

                    html.Label("Aggregation:", className="mt-2"),
                    dcc.Dropdown(AGG_FUNCS, AGG_FUNCS[0], id="table-aggfunc"),

                    html.Hr(),

                    html.H6("Calculated Fields"),
                    html.Div(id="calc-fields-container", className="mb-2"),
                    dbc.Button("➕ Add Calculated Field", id="add-calc-btn", color="secondary", outline=True, className="mb-2"),

                    html.Hr(),

                    html.H6("Filters"),
                    html.Div(id="filters-container", className="mb-2"),
                    dbc.Button("➕ Add Filter", id="add-filter-btn", color="secondary", outline=True, className="mb-2"),

                    dbc.Button("Generate Table", id="generate-table", color="primary",
                               className="mt-3 w-100")
                ])
            ], className="mb-4")
        ], width=5),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Chart Settings")),
                dbc.CardBody([
                    html.Label("X-axis:"),
                    dcc.Dropdown(id="chart-rows", multi=False, options=[]),

                    html.Label("Values:", className="mt-2"),
                    dcc.Dropdown(id="chart-vals", multi=True, options=[]),

                    html.Label("Aggregation:", className="mt-2"),
                    dcc.Dropdown(AGG_FUNCS, AGG_FUNCS[0], id="chart-aggfunc"),

                    html.Div("Chart uses the same Filters & Calculated Fields.", className="text-muted small mt-2"),

                    dbc.Button("Generate Chart", id="generate-chart", color="success",
                               className="mt-3 w-100")
                ])
            ])
        ], width=7),
    ]),

    # Output
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Pivot Table")),
                dbc.CardBody(dbc.Spinner(html.Div(id="pivot-table")))
            ], className="mb-4")
        ], width=12)
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Chart")),
                dbc.CardBody(dbc.Spinner(dcc.Graph(id="pivot-chart")))
            ])
        ], width=12)
    ])
], fluid=True)

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(left_panel, width=3),
        dbc.Col(workspace, width=9),
    ])
], fluid=True)

# =========================
# Datasets: modal, fields
# =========================
@app.callback(
    Output("dataset-modal", "is_open"),
    Input("open-dataset-modal", "n_clicks"),
    Input("ds-cancel", "n_clicks"),
    State("dataset-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_dataset_modal(open_click, cancel_click, is_open):
    return not is_open

@app.callback(
    Output("ds-source-fields", "children"),
    Input("ds-source-type", "value"),
    Input("ds-file-format", "value")
)
def render_source_fields(source_type, fmt):
    if source_type == "s3":
        return html.Div([
            dbc.Input(id="ds-s3-bucket", placeholder="S3 bucket", className="mb-2"),
            dbc.Input(id="ds-s3-key", placeholder="S3 key (path)", className="mb-2"),
        ])
    else:
        return html.Div([
            dbc.Input(id="ds-local-path", placeholder="Local file path", className="mb-2"),
        ])

def render_datasets(datasets):
    if not datasets:
        return html.Div("No datasets yet.", className="text-muted")
    items = []
    for d in datasets:
        items.append(
            dbc.ListGroupItem([
                html.Div([
                    html.Strong(d["name"]),
                    html.Span(f"  •  {d['source_type']}/{d['file_format']}", className="text-muted ms-2"),
                ]),
                dbc.Button("Use", id={"type": "use-dataset", "id": d["id"]}, size="sm", className="mt-2")
            ])
        )
    return dbc.ListGroup(items)

# SINGLE WRITER: render datasets list
@app.callback(
    Output("datasets-list", "children"),
    Input("datasets_refresh_store", "data")
)
def load_datasets(_):
    datasets, _ = get_json(DATASETS_URL)
    return render_datasets(datasets or [])

# =========================
# ✅ UNIFIED DATASET ACTIONS (Add & Use) — single writer
# =========================
@app.callback(
    Output("dataset_store", "data"),
    Output("left_alert_dataset_store", "data"),
    Output("datasets_refresh_store", "data"),
    Input("ds-add", "n_clicks"),
    Input({"type": "use-dataset", "id": ALL}, "n_clicks"),
    State("ds-name", "value"),
    State("ds-source-type", "value"),
    State("ds-file-format", "value"),
    State("ds-s3-bucket", "value"),
    State("ds-s3-key", "value"),
    State("ds-local-path", "value"),
    State("datasets_refresh_store", "data"),
    prevent_initial_call=True
)
def dataset_actions(add_click, use_clicks, name, source_type, file_format, s3_bucket, s3_key, local_path, refresh_counter):
    trig = ctx.triggered_id
    # Add dataset
    if trig == "ds-add":
        payload = {"name": name or "", "source_type": source_type, "file_format": file_format}
        if source_type == "s3":
            payload["s3"] = {"bucket": s3_bucket or "", "key": s3_key or ""}
        else:
            payload["local"] = {"path": local_path or ""}
        meta, err = post_json(DATASETS_URL, payload)
        if err:
            return no_update, alert_payload(f"Add dataset failed: {err}", True), refresh_counter
        return no_update, alert_payload(f"Added dataset: {meta.get('name')} ✅", True), (refresh_counter or 0) + 1

    # Use dataset
    if isinstance(trig, dict) and trig.get("type") == "use-dataset":
        ds_id = trig.get("id")
        return ds_id, alert_payload("Active dataset selected ✅", True), refresh_counter

    return no_update, alert_payload("No action.", True), refresh_counter

# Fetch columns when dataset changes
@app.callback(
    Output("columns_store", "data"),
    Input("dataset_store", "data"),
    prevent_initial_call=True
)
def fetch_columns_for_dataset(dataset_id):
    if not dataset_id:
        return []
    cols, err = get_json(f"{COLUMNS_URL}?dataset_id={dataset_id}")
    return cols or []

# =========================
# Reports
# =========================
def render_reports(reports):
    if not reports:
        return html.Div("No reports yet.", className="text-muted")
    items = []
    for r in reports:
        pub = " (Published)" if r.get("published") else ""
        items.append(
            dbc.ListGroupItem([
                html.Div([html.Strong(r["name"]), html.Span(pub, className="text-success ms-2")]),
                dbc.ButtonGroup([
                    dbc.Button("Open", id={"type": "open-report", "id": r["id"]}, size="sm"),
                    dbc.Button("Publish", id={"type": "publish-report", "id": r["id"]}, size="sm", color="warning", outline=True),
                    dbc.Button("View Link", id={"type": "view-report", "id": r["id"]}, size="sm", color="secondary", outline=True),
                ], className="mt-2")
            ])
        )
    return dbc.ListGroup(items)

# SINGLE WRITER: render reports list
@app.callback(
    Output("reports-list", "children"),
    Output("reports_store", "data"),
    Input("reports_refresh_store", "data")
)
def load_reports(_):
    reports, _ = get_json(REPORTS_URL)
    return render_reports(reports or []), (reports or [])

# =========================
# ✅ UNIFIED REPORT ACTIONS (Save, Open, Publish, View) — single writer
# =========================
@app.callback(
    Output("active_report_store", "data"),
    Output("left_alert_reports_store", "data"),
    Output("reports_refresh_store", "data"),
    Input("save-report", "n_clicks"),
    Input({"type": "open-report", "id": ALL}, "n_clicks"),
    Input({"type": "publish-report", "id": ALL}, "n_clicks"),
    Input({"type": "view-report", "id": ALL}, "n_clicks"),
    State("dataset_store", "data"),
    State("columns_store", "data"),
    State("calculated_fields_store", "data"),
    State("table-rows", "value"),
    State("table-cols", "value"),
    State("table-vals", "value"),
    State("table-aggfunc", "value"),
    State("chart-rows", "value"),
    State("chart-vals", "value"),
    State("chart-aggfunc", "value"),
    State("reports_store", "data"),
    State("reports_refresh_store", "data"),
    prevent_initial_call=True
)
def report_actions(save_click, open_clicks, publish_clicks, view_clicks,
                   dataset_id, columns, calcs, t_rows, t_cols, t_vals, t_agg, c_row, c_vals, c_agg,
                   reports_store, refresh_counter):

    trig = ctx.triggered_id

    # SAVE
    if trig == "save-report":
        if not dataset_id:
            return no_update, alert_payload("Select a dataset first.", True), refresh_counter
        name = f"Report {time.strftime('%Y-%m-%d %H:%M:%S')}"
        config = {
            "dataset_id": dataset_id,
            "columns": columns,
            "calculated_fields": calcs or {},
            "pivot": {"rows": t_rows or [], "columns": t_cols or [], "values": t_vals or [], "aggfunc": t_agg or "sum"},
            "chart": {"x": c_row, "values": c_vals or [], "aggfunc": c_agg or "sum"},
            "filters": {}
        }
        payload = {"name": name, "dataset_id": dataset_id, "config": config}
        saved, err = post_json(REPORTS_URL, payload)
        if err:
            return no_update, alert_payload(f"Save failed: {err}", True), refresh_counter
        return saved, alert_payload(f"Saved report: {saved.get('name')}", True), (refresh_counter or 0) + 1

    # OPEN
    if isinstance(trig, dict) and trig.get("type") == "open-report":
        rid = trig.get("id")
        rpt = next((r for r in (reports_store or []) if r["id"] == rid), None)
        if not rpt:
            return no_update, alert_payload("Report not found.", True), refresh_counter
        # TODO: populate UI from rpt["config"] if desired
        return no_update, alert_payload(f"Opened report: {rpt['name']} (apply config to UI as needed).", True), refresh_counter

    # PUBLISH
    if isinstance(trig, dict) and trig.get("type") == "publish-report":
        rid = trig.get("id")
        data, err = post_json(f"{REPORTS_URL}/{rid}/publish", {})
        if err:
            return no_update, alert_payload(f"Publish failed: {err}", True), refresh_counter
        return no_update, alert_payload(f"Published ✅ URL: {API_BASE}{data['url']}", True), (refresh_counter or 0) + 1

    # VIEW
    if isinstance(trig, dict) and trig.get("type") == "view-report":
        rid = trig.get("id")
        url = f"{API_BASE}/published/{rid}"
        return no_update, alert_payload(f"Published config at: {url}", True), refresh_counter

    return no_update, alert_payload("No report action.", True), refresh_counter

# =========================
# Calculated fields builder
# =========================
def calc_row_component(idx: int):
    return dbc.Row([
        dbc.Col(dcc.Input(id={"type": "calc-name", "index": idx}, type="text",
                          placeholder="New column (e.g., Revenue)", persistence=True, persistence_type="session",
                          style={"width": "100%"}), width=4),
        dbc.Col(dcc.Input(id={"type": "calc-formula", "index": idx}, type="text",
                          placeholder="Formula (e.g., price * quantity)", persistence=True, persistence_type="session",
                          style={"width": "100%"}), width=7),
        dbc.Col(dbc.Button("🗑", id={"type": "calc-remove", "index": idx}, color="danger", outline=True), width=1),
    ], className="mb-2", align="center")

@app.callback(
    Output("calc_rows", "data"),
    Input("add-calc-btn", "n_clicks"),
    Input({"type": "calc-remove", "index": ALL}, "n_clicks"),
    State("calc_rows", "data"),
    prevent_initial_call=True
)
def update_calc_rows(add_clicks, remove_clicks, rows):
    rows = rows or []
    trig = ctx.triggered_id
    if trig == "add-calc-btn":
        next_idx = (max(rows) + 1) if rows else 0
        return rows + [next_idx]
    if isinstance(trig, dict) and trig.get("type") == "calc-remove":
        rm = trig.get("index")
        return [i for i in rows if i != rm]
    return rows
@app.callback(
    Output("calc-fields-container", "children"),
    Input("calc_rows", "data")
)
def render_calc_rows(rows):
    rows = rows or []
    if not rows:
        return html.Div("No calculated fields added yet.", className="text-muted")
    return [calc_row_component(i) for i in rows]

@app.callback(
    Output("calculated_fields_store", "data"),
    Input("calc_rows", "data"),
    Input({"type": "calc-name", "index": ALL}, "value"),
    Input({"type": "calc-formula", "index": ALL}, "value"),
)
def sync_calculated_fields(rows, names, formulas):
    return collect_calculated_fields(names, formulas)

# =========================
# Filters builder
# =========================
def filter_row_component(idx: int, col_options):
    return dbc.Row([
        dbc.Col(dcc.Dropdown(id={"type": "filter-col", "index": idx}, options=col_options, placeholder="Choose column"), width=5),
        dbc.Col(dcc.Dropdown(id={"type": "filter-values", "index": idx}, options=[], multi=True, placeholder="Choose values"), width=6),
        dbc.Col(dbc.Button("🗑", id={"type": "filter-remove", "index": idx}, color="danger", outline=True), width=1),
    ], className="mb-2", align="center")

@app.callback(
    Output("filter_rows", "data"),
    Input("add-filter-btn", "n_clicks"),
    Input({"type": "filter-remove", "index": ALL}, "n_clicks"),
    State("filter_rows", "data"),
    prevent_initial_call=True
)
def update_filter_rows(add_clicks, remove_clicks, rows):
    rows = rows or []
    trig = ctx.triggered_id
    if trig == "add-filter-btn":
        next_idx = (max(rows) + 1) if rows else 0
        return rows + [next_idx]
    if isinstance(trig, dict) and trig.get("type") == "filter-remove":
        rm = trig.get("index")
        return [i for i in rows if i != rm]
    return rows

@app.callback(
    Output("filters-container", "children"),
    Input("filter_rows", "data"),
    State("columns_store", "data"),
    State("calculated_fields_store", "data"),
)
def render_filter_rows(rows, raw_cols, calcs_store):
    rows = rows or []
    base = raw_cols or []
    calcs = list((calcs_store or {}).keys())
    union_cols = sorted(set(base + calcs))
    col_options = [{"label": c, "value": c} for c in union_cols]
    if not rows:
        return html.Div("No filters added yet.", className="text-muted")
    return [filter_row_component(i, col_options) for i in rows]

@app.callback(
    Output({"type": "filter-values", "index": ALL}, "options"),
    Input({"type": "filter-col", "index": ALL}, "value"),
    State("dataset_store", "data"),
    State("calculated_fields_store", "data"),
    prevent_initial_call=True
)
def load_filter_values(col_selections, dataset_id, calcs_store):
    calculated_fields = calcs_store or {}
    options_lists = []
    for col in (col_selections or []):
        if not col or not dataset_id:
            options_lists.append([])
            continue
        payload = {"dataset_id": dataset_id, "column": col, "filters": {}, "calculated_fields": calculated_fields}
        data, err = post_json(DISTINCT_URL, payload)
        if err or not data:
            options_lists.append([])
            continue
        values = data.get("values", [])
        options_lists.append([{"label": str(v), "value": v} for v in values])
    return options_lists

# =========================
# CENTRALIZED options updater
# =========================
@app.callback(
    Output("table-vals", "options"),
    Output("chart-vals", "options"),
    Output("table-rows", "options"),
    Output("table-cols", "options"),
    Output("chart-rows", "options"),
    Input("columns_store", "data"),
    Input("calculated_fields_store", "data"),
)
def update_all_options(raw_cols, calcs_store):
    base = raw_cols or []
    calcs = list((calcs_store or {}).keys())
    union_cols = sorted(set(base + calcs))
    opts = [{"label": c, "value": c} for c in union_cols]
    return opts, opts, opts, opts, opts

# =========================
# Pivot Table
# =========================
@app.callback(
    Output("pivot-table", "children"),
    Output("alert_table_store", "data"),
    Input("generate-table", "n_clicks"),
    State("dataset_store", "data"),
    State("table-rows", "value"),
    State("table-cols", "value"),
    State("table-vals", "value"),
    State("table-aggfunc", "value"),
    State({"type": "filter-col", "index": ALL}, "value"),
    State({"type": "filter-values", "index": ALL}, "value"),
    State("calculated_fields_store", "data"),
    prevent_initial_call=True
)
def generate_table(_, dataset_id, rows, cols, vals, aggfunc, filter_cols, filter_vals, calcs_store):
    if not dataset_id:
        return html.Div("Select a dataset first."), {"open": True, "message": "No dataset selected.", "ts": current_ts()}

    filters = {}
    for col, values in zip(filter_cols or [], filter_vals or []):
        if col and values:
            filters[col] = values

    payload = {
        "dataset_id": dataset_id,
        "rows": rows or [],
        "columns": cols or [],
        "values": vals or [],
        "aggfunc": aggfunc,
        "filters": filters,
        "calculated_fields": calcs_store or {}
    }

    df, err = post_df(PIVOT_URL, payload)
    if err:
        return html.Div("Error fetching pivot table data."), {"open": True, "message": err, "ts": current_ts()}
    if df is None or df.empty:
        return html.Div("No data returned."), {"open": False, "message": "", "ts": current_ts()}

    total_row = {c: (df[c].sum() if pd.api.types.is_numeric_dtype(df[c]) else "Total") for c in df.columns}
    df_total = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
    table = dbc.Table.from_dataframe(df_total, striped=True, bordered=True, hover=True, responsive=True)
    return table, {"open": False, "message": "", "ts": current_ts()}

# =========================
# Chart
# =========================
@app.callback(
    Output("pivot-chart", "figure"),
    Output("alert_chart_store", "data"),
    Input("generate-chart", "n_clicks"),
    State("dataset_store", "data"),
    State("chart-rows", "value"),
    State("chart-vals", "value"),
    State("chart-aggfunc", "value"),
    State({"type": "filter-col", "index": ALL}, "value"),
    State({"type": "filter-values", "index": ALL}, "value"),
    State("calculated_fields_store", "data"),
    prevent_initial_call=True
)
def generate_chart(_, dataset_id, x_row, vals, aggfunc, filter_cols, filter_vals, calcs_store):
    if not dataset_id:
        return {}, {"open": True, "message": "No dataset selected.", "ts": current_ts()}
    if not vals or not x_row:
        return {}, {"open": True, "message": "Select X-axis and at least one value.", "ts": current_ts()}

    filters = {}
    for col, values in zip(filter_cols or [], filter_vals or []):
        if col and values:
            filters[col] = values

    payload = {
        "dataset_id": dataset_id,
        "rows": [x_row],
        "columns": [],
        "values": vals,
        "aggfunc": aggfunc,
        "filters": filters,
        "calculated_fields": (calcs_store or {})
    }

    df, err = post_df(PIVOT_URL, payload)
    if err:
        return {}, {"open": True, "message": err, "ts": current_ts()}
    if df is None or df.empty:
        return {}, {"open": False, "message": "", "ts": current_ts()}

    y_guess = f"{vals[0]}_{aggfunc}"
    y_col = y_guess if y_guess in df.columns else vals[0]
    fig = px.line(df, x=x_row, y=y_col, markers=True, title=f"{aggfunc.title()} of {vals[0]}")
    fig.update_layout(template="plotly_white", title_x=0.5)
    return fig, {"open": False, "message": "", "ts": current_ts()}

# =========================
# Central left-alert renderer (single writer to left-alert)
# =========================
@app.callback(
    Output("left-alert", "is_open"),
    Output("left-alert", "children"),
    Input("left_alert_dataset_store", "data"),
    Input("left_alert_reports_store", "data")
)
def render_left_alert(ds_alert, rpt_alert):
    alerts = [a for a in [ds_alert, rpt_alert] if a]
    if not alerts:
        return False, ""
    latest = max(alerts, key=lambda a: a.get("ts", 0))
    return latest.get("open", False), latest.get("message", "")

if __name__ == "__main__":
    app.run(debug=True, port=8050)