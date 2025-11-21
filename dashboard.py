# dash_app.py
# Full QuickSight-style pivot UI (frontend) with efficient expand/collapse
# Requirements: dash, dash-bootstrap-components, pandas, requests, plotly, dash-svg
#
# pip install dash dash-bootstrap-components pandas requests plotly dash-svg

import dash
from dash import dcc, html, Input, Output, State, ALL, ctx, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import requests
import plotly.express as px
import time
from dash_svg import Svg, Path  # requires pip install dash-svg

# ---------- Config ----------
API_BASE = "http://127.0.0.1:8000"
DATASETS_URL = f"{API_BASE}/api/datasets"
COLUMNS_URL = f"{API_BASE}/api/columns"
PIVOT_URL = f"{API_BASE}/api/pivot"

AGG_FUNCS = ["sum", "mean", "count", "max", "min"]

# ---------- App init ----------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "📊 QuickSight-style Pivot (Dash)"

# ---------- Helpers: backend comms ----------
def post_df(url, payload):
    """POST JSON payload and return DataFrame (or (None, error_msg))."""
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

# ---------- SVG helper using dash_svg ----------
def edit_svg_icon(color="#ffffff", size=14):
    """Return a dash_svg Svg pencil icon (small)."""
    # Simple pencil path (looks good at small sizes)
    return Svg([
        Path(d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z"),
        Path(d="M20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z")
    ],
    width=str(size),
    height=str(size),
    style={"verticalAlign":"middle", "display":"inline-block"},
    fill=color)

# ---------- Layout building blocks ----------
# Left dataset panel (compact)
left_panel = dbc.Card([
    dbc.CardHeader(html.H5("🧭 Datasets", className="text-white")),
    dbc.CardBody([
        dbc.Button("➕ Add Dataset", id="open-dataset-modal", color="light", outline=True, className="mb-3 w-100"),
        # Add dataset modal (keeps same UI)
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Add Dataset")),
            dbc.ModalBody([
                dbc.Input(id="ds-name", placeholder="Dataset name", className="mb-2"),
                dcc.Dropdown(id="ds-source-type", options=[{"label":"S3","value":"s3"},{"label":"Local file","value":"local"}], value="s3", className="mb-2"),
                dcc.Dropdown(id="ds-file-format", options=[{"label":"Parquet","value":"parquet"},{"label":"CSV","value":"csv"}], value="parquet", className="mb-2"),
                html.Div([html.Div([dbc.Input(id="ds-s3-bucket", placeholder="S3 bucket", className="mb-2"),
                                     dbc.Input(id="ds-s3-key", placeholder="S3 key (prefix or key)", className="mb-2")], id="s3-fields"),
                          html.Div([dbc.Input(id="ds-local-path", placeholder="Local file path", className="mb-2")], id="local-fields")], id="ds-source-fields")
            ]),
            dbc.ModalFooter([dbc.Button("Cancel", id="ds-cancel"), dbc.Button("Add", id="ds-add", color="primary")])
        ], id="dataset-modal", is_open=False),
        html.Div(id="datasets-list", className="mt-2 text-white")
    ])
], style={"backgroundColor":"#2F3E46", "height":"100vh", "border":"none"})

# Utility card maker
def make_card(title, children):
    return dbc.Card([dbc.CardHeader(html.H5(title, className="fw-bold")), dbc.CardBody(children)],
                    className="mb-3 shadow-sm", style={"backgroundColor":"#F8F9FA","borderRadius":"8px"})

# Calculated fields cards (kept simple)
calc_fields_table = make_card("Pivot Table Calculated Fields", [
    html.Div(id="calculated-fields-container"),
    dbc.Button("➕ Add Field", id="add-calc-field-table", color="secondary", className="mt-2")
])
calc_fields_chart = make_card("Chart Calculated Fields", [
    html.Div(id="calc-fields-chart-container"),
    dbc.Button("➕ Add Field", id="add-calc-field-chart", color="secondary", className="mt-2")
])

# Rename modal (opens when user clicks pencil)
rename_modal = dbc.Modal([
    dbc.ModalHeader("Rename Column"),
    dbc.ModalBody(dbc.Input(id="rename-input", placeholder="Enter new column name", type="text", style={"width":"100%"})),
    dbc.ModalFooter([dbc.Button("Save", id="rename-save", color="primary"), dbc.Button("Cancel", id="rename-cancel", color="secondary", className="ms-2")])
], id="rename-modal", is_open=False, backdrop="static")

# Workspace container (stores + UI)
workspace = dbc.Container([
    # Stores
    dcc.Store(id="columns_store", data=[]),
    dcc.Store(id="datasets_refresh_store", data=0),
    dcc.Store(id="calculated_fields_store", data=[]),
    dcc.Store(id="calculated_fields_chart_store", data=[]),
    dcc.Store(id="header_name_map_store", data={}),  # mapping: original_col -> display_name
    dcc.Store(id="rename-target", data=None),
    dcc.Store(id="collapsed_store", data={}), 
    dcc.Store(id="filters-store", data=[]), # mapping: row_key -> collapsed_boolean (reserved for future use)

    html.Div(html.Label("Rename headers: click the pencil icon to rename a column."), style={"marginBottom":"6px"}),

    dbc.Row([
        dbc.Col(make_card("Pivot Table Settings", [
            html.Label("Dataset:"), dcc.Dropdown(id="table-dataset", options=[], placeholder="Select dataset", className="mb-2"),
            html.Label("Rows:"), dcc.Dropdown(id="table-rows", multi=True, options=[]),
            html.Label("Columns:"), dcc.Dropdown(id="table-cols", multi=True, options=[]),
            html.Label("Values:"), dcc.Dropdown(id="table-vals", multi=True, options=[]),
            html.Label("Aggregation:"), dcc.Dropdown(id="table-aggfunc", options=[{"label":a,"value":a} for a in AGG_FUNCS], value=AGG_FUNCS[0]),
            calc_fields_table,
            html.Label("Filters:"),
            html.Div([
            dbc.Button("➕ Add Filter", id="add-filter-table-btn", color="secondary", className="mb-2"),
            html.Div(id="filters-table-container")
            ], style={"marginBottom": "10px"}),

            dbc.Button("Generate Table", id="generate-table", color="primary", className="mt-3 w-100")
        ]), width=5),

        dbc.Col(make_card("Chart Settings", [
            html.Label("Dataset:"), dcc.Dropdown(id="chart-dataset", options=[], placeholder="Select dataset", className="mb-2"),
            html.Label("X-axis:"), dcc.Dropdown(id="chart-rows", multi=False, options=[]),
            html.Label("Values:"), dcc.Dropdown(id="chart-vals", multi=True, options=[]),
            html.Label("Aggregation:"), dcc.Dropdown(id="chart-aggfunc", options=[{"label":a,"value":a} for a in AGG_FUNCS], value=AGG_FUNCS[0]),
            calc_fields_chart,
            dbc.Button("Generate Chart", id="generate-chart", color="success", className="mt-3 w-100")
        ]), width=7),
    ], className="mb-3"),

    dbc.Row(dbc.Col(make_card("Pivot Table", [dbc.Spinner(html.Div(id="pivot-table"))]), width=12)),
    dbc.Row(dbc.Col(make_card("Chart", dcc.Graph(id="pivot-chart")), width=12)),

    rename_modal
], fluid=True, style={"padding":"20px", "backgroundColor":"#E5E5E5"})

app.layout = dbc.Container([dbc.Row([dbc.Col(left_panel, width=3), dbc.Col(workspace, width=9)])], fluid=True)

# plotly defaults
px.defaults.template = "plotly_white"

# ---------- Dataset callbacks (unchanged logic) ----------
@app.callback(Output("dataset-modal","is_open"),
              Input("open-dataset-modal","n_clicks"),
              Input("ds-cancel","n_clicks"),
              Input("ds-add","n_clicks"),
              State("dataset-modal","is_open"),
              prevent_initial_call=True)
def toggle_dataset_modal(open_click, cancel_click, add_click, is_open):
    trig = ctx.triggered_id
    if trig == "open-dataset-modal":
        return True
    if trig in ("ds-cancel","ds-add"):
        return False
    return is_open

@app.callback(Output("s3-fields","style"), Output("local-fields","style"),
              Input("ds-source-type","value"))
def toggle_source_fields(source_type):
    if source_type == "s3":
        return {"display":"block"}, {"display":"none"}
    return {"display":"none"}, {"display":"block"}

def render_datasets(datasets):
    if not datasets:
        return html.Div("No datasets yet.", className="text-muted")
    items = []
    for d in datasets:
        items.append(dbc.ListGroupItem([
            html.Div([html.Strong(d.get("name", d.get("id"))),
                      html.Span(f" • {d.get('source_type','?')}/{d.get('file_format','?')}", className="text-muted ms-2")]),
            dbc.Button("Use", id={"type":"use-dataset","id":d["id"]}, size="sm", className="mt-2")
        ]))
    return dbc.ListGroup(items)

@app.callback(Output("datasets-list","children"), Input("datasets_refresh_store","data"))
def load_datasets(_):
    datasets, err = get_json(DATASETS_URL)
    if err:
        return html.Div(f"Failed to load datasets: {err}", className="text-danger")
    return render_datasets(datasets or [])

@app.callback(Output("datasets_refresh_store","data"),
              Input("ds-add","n_clicks"),
              State("ds-name","value"),
              State("ds-source-type","value"),
              State("ds-file-format","value"),
              State("ds-s3-bucket","value"),
              State("ds-s3-key","value"),
              State("ds-local-path","value"),
              State("datasets_refresh_store","data"),
              prevent_initial_call=True)
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

@app.callback(Output("table-dataset","value"), Output("chart-dataset","value"),
              Input({"type":"use-dataset","id":ALL},"n_clicks"),
              State({"type":"use-dataset","id":ALL},"id"),
              prevent_initial_call=True)
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

@app.callback(Output("table-dataset","options"), Output("chart-dataset","options"),
              Input("datasets_refresh_store","data"))
def update_dataset_options(_):
    datasets, err = get_json(DATASETS_URL)
    if err:
        return [], []
    options = [{"label": d.get("name", d.get("id")), "value": d["id"]} for d in (datasets or [])]
    return options, options

@app.callback(Output("columns_store","data"),
              Input("table-dataset","value"),
              Input("chart-dataset","value"))
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

# ---------- Calculated fields (kept same logic) ----------
@app.callback(Output("calculated-fields-container","children"),
              Output("calc-fields-chart-container","children"),
              Input("add-calc-field-table","n_clicks"),
              Input("add-calc-field-chart","n_clicks"),
              State("calculated-fields-container","children"),
              State("calc-fields-chart-container","children"),
              prevent_initial_call=True)
def update_calc_fields(add_table_clicks, add_chart_clicks, table_children, chart_children):
    table_children = table_children or []
    chart_children = chart_children or []
    trig = ctx.triggered_id
    ts = str(time.time()).replace('.', '')
    short_ts = ts[-8:]
    if trig == "add-calc-field-table":
        default_name = f"calc_{short_ts}"
        row = dbc.Row([dbc.Col(dbc.Input(id={"type":"calc-name","index":ts}, placeholder="Field name", value=default_name), width=4),
                       dbc.Col(dbc.Input(id={"type":"calc-formula","index":ts}, placeholder="Formula", value=""), width=6),
                       dbc.Col(dbc.Button("Save", id={"type":"save-calc","index":ts}, color="primary", n_clicks=0), width=2)],
                      className="mb-1", id={"type":"calc-row","index":ts})
        table_children.append(row)
    elif trig == "add-calc-field-chart":
        default_name = f"calcc_{short_ts}"
        row = dbc.Row([dbc.Col(dbc.Input(id={"type":"calc-name-chart","index":ts}, placeholder="Field name", value=default_name), width=4),
                       dbc.Col(dbc.Input(id={"type":"calc-formula-chart","index":ts}, placeholder="Formula", value=""), width=6),
                       dbc.Col(dbc.Button("Save", id={"type":"save-calc-chart","index":ts}, color="primary", n_clicks=0), width=2)],
                      className="mb-1", id={"type":"calc-row-chart","index":ts})
        chart_children.append(row)
    return table_children, chart_children

@app.callback(Output("calculated_fields_store","data"),
              Input({"type":"save-calc","index":ALL},"n_clicks"),
              State({"type":"save-calc","index":ALL},"id"),
              State({"type":"calc-name","index":ALL},"id"),
              State({"type":"calc-name","index":ALL},"value"),
              State({"type":"calc-formula","index":ALL},"id"),
              State({"type":"calc-formula","index":ALL},"value"),
              State("calculated_fields_store","data"),
              prevent_initial_call=True)
def save_calc_field(n_clicks_list, save_btn_ids, name_ids, all_names, formula_ids, all_formulas, store):
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

@app.callback(Output("calculated_fields_chart_store","data"),
              Input({"type":"save-calc-chart","index":ALL},"n_clicks"),
              State({"type":"save-calc-chart","index":ALL},"id"),
              State({"type":"calc-name-chart","index":ALL},"id"),
              State({"type":"calc-name-chart","index":ALL},"value"),
              State({"type":"calc-formula-chart","index":ALL},"id"),
              State({"type":"calc-formula-chart","index":ALL},"value"),
              State("calculated_fields_chart_store","data"),
              prevent_initial_call=True)
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

# ---------- Populate dropdowns ----------
@app.callback(Output("table-rows","options"),
              Output("table-cols","options"),
              Output("table-vals","options"),
              Output("chart-rows","options"),
              Output("chart-vals","options"),
              Input("columns_store","data"),
              Input("calculated_fields_store","data"),
              Input("calculated_fields_chart_store","data"))
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

@app.callback(Output("table-vals","value"),
              Input("calculated_fields_store","data"),
              State("table-vals","value"))
def auto_select_calc_fields(calc_store, current_vals):
    calc_names = [f["name"] for f in (calc_store or [])]
    current_vals = current_vals or []
    for c in calc_names:
        if c not in current_vals:
            current_vals.append(c)
    return current_vals

@app.callback(Output("chart-vals","value"),
              Input("calculated_fields_chart_store","data"),
              State("chart-vals","value"))
def auto_select_calc_fields_chart(calc_store, current_vals):
    calc_names = [f["name"] for f in (calc_store or [])]
    current_vals = current_vals or []
    for c in calc_names:
        if c not in current_vals:
            current_vals.append(c)
    return current_vals

# ---------- Merged rename callback ----------
@app.callback(Output("rename-modal","is_open"),
              Output("header_name_map_store","data"),
              Output("rename-target","data"),
              Output("rename-input","value"),
              Input({"type":"rename-btn","col":ALL},"n_clicks"),
              Input("rename-save","n_clicks"),
              Input("rename-cancel","n_clicks"),
              State("header_name_map_store","data"),
              State("rename-target","data"),
              State("rename-input","value"),
              prevent_initial_call=True)
def handle_rename(btn_clicks, save_click, cancel_click, header_map, rename_target, rename_input):
    triggered = ctx.triggered_id
    header_map = header_map or {}
    # user clicked an inline rename button
    if isinstance(triggered, dict) and triggered.get("type") == "rename-btn":
        col = triggered.get("col")
        current_display = header_map.get(col, col)
        return True, header_map, col, current_display
    # user clicked Save
    if triggered == "rename-save":
        if rename_target and rename_input and str(rename_input).strip():
            header_map = header_map or {}
            header_map[rename_target] = str(rename_input).strip()
        return False, header_map, None, ""
    # user clicked Cancel
    if triggered == "rename-cancel":
        return False, header_map, None, ""
    return no_update, no_update, no_update, no_update


@app.callback(
    Output("filters-table-container", "children"),
    Output("filters-store", "data"),  # ✅ fixed id
    Input("add-filter-table-btn", "n_clicks"),
    State("columns_store", "data"),
    State("filters-store", "data"),   # ✅ fixed id
    prevent_initial_call=True
)
def add_table_filter(n, columns, stored_filters):
    if not columns:
        return no_update, no_update

    stored_filters = stored_filters or []
    index = len(stored_filters)

    stored_filters.append({"index": index})

    children = []
    for f in stored_filters:
        i = f["index"]
        children.append(
            html.Div([
                dcc.Dropdown(
                    id={"type": "filter-col-table", "index": i},
                    options=[{"label": c, "value": c} for c in columns],
                    placeholder="Select column",
                    className="mb-1"
                ),
                dcc.Dropdown(
                    id={"type": "filter-val-table", "index": i},
                    placeholder="Select value",
                    className="mb-2"
                )
            ])
        )

    return children, stored_filters




# ---------- Generate Pivot Table ----------
# NOTE: This callback now responds to both button click and header_name_map_store changes.
@app.callback(Output("pivot-table","children"),
              Input("generate-table","n_clicks"),
              Input("header_name_map_store","data"),
              Input({"type": "filter-col-table", "index": ALL}, "value"),
              Input({"type": "filter-val-table", "index": ALL}, "value"),
              State("table-dataset","value"),
              State("table-rows","value"),
              State("table-cols","value"),
              State("table-vals","value"),
              State("table-aggfunc","value"),
              State("calculated_fields_store","data"),
              prevent_initial_call=False)
def generate_table(n_clicks, header_map,filter_cols, filter_vals, ds, rows, cols, vals, aggfunc, calc_store):
    if not ds:
        return html.Div("Select a dataset and click Generate Table.", className="text-muted")

    calculated_fields = [{"name": f["name"], "formula": f["formula"]} for f in (calc_store or [])]

    # ✅ Prepare filters for backend
    filters = []
    if filter_cols and filter_vals:
        for c, v in zip(filter_cols, filter_vals):
            if c and v:
                filters.append({"column": c, "value": v})

    payload = {"dataset_id": ds, "rows": rows or [], "columns": cols or [], "values": vals or [], "aggfunc": aggfunc, "calculated_fields": calculated_fields,"filters": filters}

    df, err = post_df(PIVOT_URL, payload)
    if err or df is None:
        return html.Div(f"No data found. {err or ''}", className="text-muted")
    if df.empty:
        return html.Div("No rows returned.", className="text-muted")

    header_map = header_map or {}
    display_cols = [header_map.get(c, c) for c in df.columns]

    # ---------- Header ----------
    header_style = {
        "backgroundColor": "#670178", "color": "white", "fontWeight": "bold",
        "textAlign": "center", "padding": "8px", "borderBottom": "2px solid #555",
        "borderRight": "1px solid #bbb", "position": "sticky", "top": "0", "zIndex": "3"
    }

    th_cells = []
    for orig_col, disp in zip(df.columns, display_cols):
        rename_btn = html.Button(edit_svg_icon(color="#ffffff", size=14),
                                 id={"type":"rename-btn","col":orig_col},
                                 n_clicks=0, title=f"Rename {orig_col}",
                                 style={"border":"none","background":"transparent","cursor":"pointer","padding":"0","marginLeft":"6px","display":"inline-flex","alignItems":"center"})
        th_html = html.Div([html.Span(disp), rename_btn], style={"display":"inline-flex","alignItems":"center","gap":"6px"})
        th_cells.append((orig_col, th_html))

    table_header = html.Tr([html.Th(th_cells[0][1], style={**header_style, "left":"0","zIndex":"4"}),
                            *[html.Th(h, style=header_style) for _, h in th_cells[1:]]])

    # ---------- Rows ----------
    n_row_dims = len(rows or [])
    table_rows = []
    total_row = None

    # --- Correct parent-child keys ---
    row_keys = []
    seen_parents = [{} for _ in range(n_row_dims)]  # track last value at each level
    for i, r in df.iterrows():
        labels = []
        for k in range(n_row_dims):
            val = "" if pd.isna(r.iloc[k]) else str(r.iloc[k])
            if not val:
                val = seen_parents[k].get("value", "")
            else:
                seen_parents[k]["value"] = val
            for deeper in range(k+1, n_row_dims):
                seen_parents[deeper]["value"] = ""
            labels.append(val)
        full_key = "||".join(labels)
        parent_key = "||".join(labels[:-1]) if n_row_dims > 1 else ""
        row_keys.append((full_key, parent_key))

    # Build children map
    children_map = {}
    for idx, (k, p) in enumerate(row_keys):
        children_map.setdefault(p, []).append(k)

    # Cell style
    def cell_style(level=0, is_first=False, is_total=False):
        s = {"padding":"6px","paddingLeft": f"{20*level + 6}px","borderRight":"1px solid #ccc","borderBottom":"1px solid #ccc","whiteSpace":"nowrap","overflow":"hidden","textOverflow":"ellipsis","backgroundColor":"white","textAlign":"center"}
        if is_first:
            s.update({"position":"sticky","left":"0","zIndex":"2","backgroundColor":"white"})
        if is_total:
            s.update({"backgroundColor":"#670178","color":"white","fontWeight":"bold"})
        return s

    # Build TRs
    for i, r in df.iterrows():
        labels = []
        for k in range(min(n_row_dims, len(df.columns))):
            labels.append("" if pd.isna(r.iloc[k]) else str(r.iloc[k]))
        full_key, parent_key = row_keys[i]
        first_val = labels[0].lower() if labels and labels[0] else ""
        is_total = "total" in first_val
        cells = []
        for j, col in enumerate(df.columns):
            is_first = j == 0
            style = cell_style(level=j if j < n_row_dims else 0, is_first=is_first, is_total=is_total)
            if is_first:
                has_children = full_key in children_map and len(children_map[full_key]) > 0
                if not is_total and has_children:
                    exp = html.Button("▶", id={"type":"expander","row_key":full_key}, n_clicks=0,
                                      title="Expand / Collapse",
                                      style={"border":"none","background":"none","cursor":"pointer","marginRight":"6px","fontSize":"12px","lineHeight":"12px"})
                    cells.append(html.Td([exp, r[col]], style=style))
                else:
                    spacer = html.Span(style={"display":"inline-block","width":"16px","height":"12px","marginRight":"6px"})
                    cells.append(html.Td([spacer, r[col]], style=style))
            else:
                cells.append(html.Td(r[col], style=style))
        tr = html.Tr(cells, **{"data-key": full_key, "data-parent-key": parent_key, "className":"pivot-row"})
        if is_total:
            total_row = tr
        else:
            table_rows.append(tr)
    if total_row:
        table_rows.append(total_row)

    # ---------- JS expand/collapse (unchanged) ----------
    script = html.Script(f"""
    (function(){{
        setTimeout(() => {{
            const rows = Array.from(document.querySelectorAll("tr.pivot-row"));
            const childrenMap = new Map();
            rows.forEach(r => {{
                const key = r.getAttribute('data-key') || '';
                const parent = r.getAttribute('data-parent-key') || '';
                if (!childrenMap.has(parent)) childrenMap.set(parent, []);
                childrenMap.get(parent).push(key);
            }});
            const rowByKey = new Map();
            rows.forEach(r => rowByKey.set(r.getAttribute('data-key') || '', r));
            function hideDescendantsIterative(rootKey) {{
                const stack = (childrenMap.get(rootKey) || []).slice();
                while (stack.length) {{
                    const childKey = stack.pop();
                    const childRow = rowByKey.get(childKey);
                    if (!childRow) continue;
                    childRow.style.display = 'none';
                    const childBtn = childRow.querySelector("button[id*='expander']");
                    if (childBtn) childBtn.innerText = "▶";
                    const grandchildren = childrenMap.get(childKey) || [];
                    for (let g of grandchildren) stack.push(g);
                }}
            }}
            function showDirectChildren(rootKey) {{
                const direct = childrenMap.get(rootKey) || [];
                for (let k of direct) {{
                    const r = rowByKey.get(k);
                    if (r) r.style.display = '';
                }}
            }}
            rows.forEach(r => {{
                const parent = r.getAttribute('data-parent-key') || '';
                if (parent) r.style.display = 'none';
            }});
            document.querySelectorAll("button[id*='expander']").forEach(btn => {{
                btn.addEventListener("click", (ev) => {{
                    ev.stopPropagation();
                    const tr = btn.closest('tr');
                    if (!tr) return;
                    const key = tr.getAttribute('data-key') || '';
                    const expanding = btn.innerText === "▶";
                    btn.innerText = expanding ? "▼" : "▶";
                    if (expanding) showDirectChildren(key); else hideDescendantsIterative(key);
                }});
            }});
        }}, 100);
    }})();
    """)

    table_style = {"width":"100%","borderCollapse":"collapse","tableLayout":"fixed"}
    container_style = {"overflowX":"auto","maxHeight":"100%","border":"1px solid #ccc","borderRadius":"6px","backgroundColor":"white"}

    return html.Div([html.Table([html.Thead(table_header), html.Tbody(table_rows)], style=table_style), script], style=container_style)

# ---------- Chart generator (unchanged) ----------
@app.callback(Output("pivot-chart","figure"),
              Input("generate-chart","n_clicks"),
              State("chart-dataset","value"),
              State("chart-rows","value"),
              State("chart-vals","value"),
              State("chart-aggfunc","value"),
              State("calculated_fields_chart_store","data"),
              prevent_initial_call=True)
def generate_chart(n, ds, x_col, vals, aggfunc, calc_store):
    if not ds or not x_col:
        return {}
    calculated_fields = [{"name": f["name"], "formula": f["formula"]} for f in (calc_store or [])]
    payload = {"dataset_id": ds, "rows":[x_col], "columns":[], "values": vals or [], "aggfunc": aggfunc, "calculated_fields": calculated_fields}
    df, err = post_df(PIVOT_URL, payload)
    if err or df is None or df.empty:
        return {}
    y_cols = vals if vals else [c for c in df.columns if c != x_col]
    fig = px.bar(df, x=x_col, y=y_cols, barmode="group")
    return fig

# ---------- Run ----------
if __name__ == "__main__":
    app.run(debug=True, port=8050)
