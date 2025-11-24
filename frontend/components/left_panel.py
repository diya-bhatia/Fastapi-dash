import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

def build_left_panel():
    return dbc.Card(
        [
            dbc.Accordion(
                [
                    # -------- Datasets Section --------
                    dbc.AccordionItem(
                        [
                            dbc.Button(
                                "➕ Add Dataset",
                                id="open-dataset-modal",
                                color="light",
                                outline=True,
                                className="mb-2 w-100"
                            ),
                            dbc.Button(
                                "Datasets",
                                id="datasets-btn",
                                color="light",
                                outline=True,
                                className="mb-2 w-100"
                            ),
                            html.Div(id="datasets-list", className="mt-2 text-white"),

                            # Dataset Modal
                            dbc.Modal(
                                [
                                    dbc.ModalHeader(dbc.ModalTitle("Add Dataset")),
                                    dbc.ModalBody(
                                        [
                                            dbc.Input(id="ds-name", placeholder="Dataset name", className="mb-2"),
                                            dcc.Dropdown(
                                                id="ds-source-type",
                                                options=[
                                                    {"label": "S3", "value": "s3"},
                                                    {"label": "Local file", "value": "local"}
                                                ],
                                                value="s3",
                                                className="mb-2"
                                            ),
                                            dcc.Dropdown(
                                                id="ds-file-format",
                                                options=[
                                                    {"label": "Parquet", "value": "parquet"},
                                                    {"label": "CSV", "value": "csv"}
                                                ],
                                                value="parquet",
                                                className="mb-2"
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            dbc.Input(id="ds-s3-bucket", placeholder="S3 bucket", className="mb-2"),
                                                            dbc.Input(id="ds-s3-key", placeholder="S3 key", className="mb-2")
                                                        ],
                                                        id="s3-fields"
                                                    ),
                                                    html.Div(
                                                        [dbc.Input(id="ds-local-path", placeholder="Local file path", className="mb-2")],
                                                        id="local-fields"
                                                    )
                                                ],
                                                id="ds-source-fields"
                                            )
                                        ]
                                    ),
                                    dbc.ModalFooter(
                                        [
                                            dbc.Button("Cancel", id="ds-cancel"),
                                            dbc.Button("Add", id="ds-add", color="primary")
                                        ]
                                    )
                                ],
                                id="dataset-modal",
                                is_open=False,
                                backdrop=True
                            ),
                        ],
                        title="🧭 Datasets"
                    ),

                    # -------- Analyses Section --------
                    dbc.AccordionItem(
                        [
                            dbc.Button(
                                "➕ New Analysis",
                                id="new-analysis-btn",
                                color="light",
                                outline=True,
                                className="mb-2 w-100"
                            ),
                            html.Div(id="analyses-list", className="mt-2 text-white")
                        ],
                        title="📊 Analyses"
                    ),

                    # -------- Published Dashboards Section --------
                    dbc.AccordionItem(
                        [
                            dbc.Button(
                                "Dashboards",
                                id="dashboards-btn",
                                color="light",
                                outline=True,
                                className="mb-2 w-100"
                            ),
                            html.Div(id="dashboards-list", className="mt-2 text-white")
                        ],
                        title="📌 Published Dashboards"
                    ),
                ],
                start_collapsed=True
            )
        ],
        style={
            "backgroundColor": "#2F3E46",
            "height": "100vh",
            "border": "none",
            "position": "fixed",
            "top": "0",
            "left": "0",
            "width": "240px",
            "zIndex": "1000",
            "padding": "15px",
            "overflowY": "auto"
        }
    )
