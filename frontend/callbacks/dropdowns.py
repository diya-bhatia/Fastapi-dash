from dash import Input, Output, State

def register_dropdown_callbacks(app):

    @app.callback(
        Output("table-rows","options"),
        Output("table-cols","options"),
        Output("table-vals","options"),
        Output("chart-rows","options"),
        Output("chart-vals","options"),
        Input("columns_store","data"),
        Input("calculated_fields_store","data"),
        Input("calculated_fields_chart_store","data")
    )
    def populate_dropdowns(columns, calc_store, calc_store_chart):
        calc_names = [f["name"] for f in (calc_store or [])]
        calc_names_chart = [f["name"] for f in (calc_store_chart or [])]

        def make_options(base, extra):
            seen=set()
            out=[]
            for c in (base or []) + extra:
                if c not in seen:
                    seen.add(c)
                    out.append({"label":c,"value":c})
            return out

        table_opts = make_options(columns, calc_names)
        chart_opts = make_options(columns, calc_names_chart)

        return table_opts,table_opts,table_opts,chart_opts,chart_opts
