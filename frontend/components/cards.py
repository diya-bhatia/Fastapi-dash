import dash_bootstrap_components as dbc
from dash import html

def make_card(title, children):
    return dbc.Card(
        [
            dbc.CardHeader(html.H5(title, className="fw-bold")),
            dbc.CardBody(children)
        ],
        className="mb-3 shadow-sm",
        style={"backgroundColor": "#F8F9FA", "borderRadius": "8px"}
    )


