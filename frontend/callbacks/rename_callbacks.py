from dash import Input, Output, State, ctx, no_update
from dash import ALL

def register_rename_callbacks(app):

    @app.callback(
        Output("rename-modal","is_open"),
        Output("header_name_map_store","data"),
        Output("rename-target","data"),
        Output("rename-input","value"),
        Input({"type":"rename-btn","col":ALL},"n_clicks"),
        Input("rename-save","n_clicks"),
        Input("rename-cancel","n_clicks"),
        State("header_name_map_store","data"),
        State("rename-target","data"),
        State("rename-input","value"),
        prevent_initial_call=True
    )
    def handle_rename(btn_clicks, save_click, cancel_click, header_map, target, rename_input):
        triggered = ctx.triggered_id
        header_map = header_map or {}

        if isinstance(triggered, dict):
            col = triggered.get("col")
            return True, header_map, col, header_map.get(col,col)

        if triggered == "rename-save":
            if target and rename_input:
                header_map[target] = rename_input.strip()
            return False, header_map, None, ""

        if triggered == "rename-cancel":
            return False, header_map, None, ""

        return no_update,no_update,no_update,no_update
