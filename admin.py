import dash
from dash import dcc, html, Input, Output, State, dash_table
import requests

# Fetch column names from FastAPI
try:
    columns = requests.get("http://localhost:8000/columns").json()
except Exception as e:
    columns = []
    print("Error fetching columns:", e)

admin_app = dash.Dash(__name__, title="Admin Dashboard")

admin_app.layout = html.Div([
    html.H2("Pivot Table Builder"),

    dcc.Dropdown(
        id="index",
        options=[{"label": col, "value": col} for col in columns],
        multi=True,
        placeholder="Group by (index)"
    ),

    dcc.Dropdown(
        id="columns",
        options=[{"label": col, "value": col} for col in columns],
        multi=True,
        placeholder="Columns"
    ),

    dcc.Dropdown(
        id="values",
        options=[{"label": col, "value": col} for col in columns],
        multi=True,
        placeholder="Values"
    ),

    dcc.Dropdown(
        id="aggfunc",
        options=[{"label": f, "value": f} for f in ["sum", "mean", "count"]],
        value="sum",
        placeholder="Aggregation Function"
    ),

    html.Button("Generate Pivot", id="generate"),

    html.Div(id="debug-output", style={"whiteSpace": "pre-wrap", "marginTop": "20px"}),

    dash_table.DataTable(id="pivot-table", page_size=10)
])

@admin_app.callback(
    Output("pivot-table", "data"),
    Output("pivot-table", "columns"),
    Output("debug-output", "children"),
    Input("generate", "n_clicks"),
    State("index", "value"),
    State("columns", "value"),
    State("values", "value"),
    State("aggfunc", "value")
)
def update_pivot(n, index, columns, values, aggfunc):
    if not n:
        return [], [], ""

    # Auto-switch to 'count' if no values selected
    if not values:
        aggfunc = "count"

    payload = {
        "index": index or [],
        "columns": columns or [],
        "values": values or [],
        "aggfunc": aggfunc
    }

    try:
        res = requests.post("http://localhost:8000/pivot", json=payload)
        response_json = res.json()
        pivot_data = response_json.get("pivot", [])

        table_columns = [{"name": k, "id": k} for k in pivot_data[0].keys()] if pivot_data else []
        debug_text = f"Payload sent:\n{payload}\n\nResponse:\n{pivot_data[:5]}..." if pivot_data else "No data returned."
        return pivot_data, table_columns, debug_text
    except Exception as e:
        return [], [], f"Error generating pivot:\n{str(e)}"

if __name__ == "__main__":
    admin_app.run(debug=True)