import requests
import dash_bootstrap_components as dbc
from dash import html, ctx, no_update
from dash import Input, Output, State, ALL

# Import your project configs/helpers
from config import API_BASE, DATASETS_URL, COLUMNS_URL
from services.api_client import get_json


def register_dataset_callbacks(app):
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
        elif trig in ("ds-cancel", "ds-add"):
            return False

        return is_open


    # ============================
    # Toggle S3 / Local Fields
    # ============================
    @app.callback(
        Output("s3-fields", "style"),
        Output("local-fields", "style"),
        Input("ds-source-type", "value")
    )
    def toggle_source_fields(source_type):
        if source_type == "s3":
            return {"display": "block"}, {"display": "none"}

        return {"display": "none"}, {"display": "block"}


    # ============================
    # Render Datasets List
    # ============================
    def render_datasets(datasets):
        if not datasets:
            return html.Div("No datasets yet.", className="text-muted")

        items = []
        for d in datasets:
            items.append(
                dbc.ListGroupItem([
                    html.Div([
                        html.Strong(d.get("name", d.get("id"))),
                        html.Span(
                            f" • {d.get('source_type','?')}/{d.get('file_format','?')}",
                            className="text-muted ms-2"
                        )
                    ]),
                    dbc.Button(
                        "Use",
                        id={"type": "use-dataset", "id": d["id"]},
                        size="sm",
                        className="mt-2"
                    )
                ])
            )

        return dbc.ListGroup(items)


    # ============================
    # Load Datasets
    # ============================
    @app.callback(
        Output("datasets-list", "children"),
        Input("datasets_refresh_store", "data")
    )
    def load_datasets(_):
        datasets, err = get_json(DATASETS_URL)

        if err:
            return html.Div(f"Failed to load datasets: {err}", className="text-danger")

        return render_datasets(datasets or [])


    # ============================
    # Add Dataset
    # ============================
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
    def add_dataset(n_clicks, name, source_type, file_format,
                    s3_bucket, s3_key, local_path, refresh_counter):
        if not n_clicks:
            return no_update

        payload = {
            "name": name or "",
            "source_type": source_type,
            "file_format": file_format
        }

        if source_type == "s3":
            payload["s3"] = {
                "bucket": (s3_bucket or "").strip(),
                "key": (s3_key or "").strip()
            }
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


    # ============================
    # Use Selected Dataset
    # ============================
    @app.callback(
        Output("table-dataset", "value"),
        Output("chart-dataset", "value"),
        Input({"type": "use-dataset", "id": ALL}, "n_clicks"),
        State({"type": "use-dataset", "id": ALL}, "id"),
        prevent_initial_call=True
    )
    def use_dataset(n_clicks_list, ids):
        if not n_clicks_list or not ids:
            return no_update, no_update

        for i, clicks in enumerate(n_clicks_list):
            if clicks:
                dataset_id = ids[i]["id"]

                try:
                    res = requests.post(f"{API_BASE}/api/activate_dataset/{dataset_id}", timeout=10)
                    res.raise_for_status()
                except Exception as e:
                    print("Failed to activate dataset:", e)

                return dataset_id, dataset_id

        return no_update, no_update


    # ============================
    # Update Dataset Dropdowns
    # ============================
    @app.callback(
        Output("table-dataset", "options"),
        Output("chart-dataset", "options"),
        Input("datasets_refresh_store", "data")
    )
    def update_dataset_options(_):
        datasets, err = get_json(DATASETS_URL)

        if err:
            return [], []

        options = [
            {"label": d.get("name", d.get("id")), "value": d["id"]}
            for d in (datasets or [])
        ]

        return options, options


    # ============================
    # Fetch Columns
    # ============================
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
