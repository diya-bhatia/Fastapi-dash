from dash import Input, Output, State
import plotly.express as px
from services.api_client import post_df
from config import PIVOT_URL

def register_chart_callbacks(app):

    @app.callback(
        Output("pivot-chart","figure"),
        Input("generate-chart","n_clicks"),
        State("chart-dataset","value"),
        State("chart-rows","value"),
        State("chart-vals","value"),
        State("chart-aggfunc","value"),
        prevent_initial_call=True
    )
    def generate_chart(n, ds, x_col, vals, aggfunc):
        if not ds or not x_col:
            return {}

        payload = {
            "dataset_id": ds,
            "rows":[x_col],
            "values": vals or [],
            "aggfunc": aggfunc
        }

        df, err = post_df(PIVOT_URL, payload)
        if err or df is None or df.empty:
            return {}

        return px.bar(df, x=x_col, y=vals)
