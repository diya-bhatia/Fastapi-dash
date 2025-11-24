from dash import Input, Output, State, no_update, html, dcc

def register_filter_callbacks(app):

    @app.callback(
        Output("filters-table-container","children"),
        Output("filters-store","data"),
        Input("add-filter-table-btn","n_clicks"),
        State("columns_store","data"),
        State("filters-store","data"),
        prevent_initial_call=True
    )
    def add_table_filter(n, columns, stored):
        if not columns:
            return no_update,no_update

        stored = stored or []
        idx = len(stored)
        stored.append({"index":idx})

        children=[]
        for f in stored:
            i=f["index"]
            children.append(html.Div([
                dcc.Dropdown(
                    id={"type":"filter-col-table","index":i},
                    options=[{"label":c,"value":c} for c in columns]
                ),
                dcc.Dropdown(
                    id={"type":"filter-val-table","index":i}
                )
            ]))

        return children, stored
