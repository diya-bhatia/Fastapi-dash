import dash_bootstrap_components as dbc
from dash import html

def home_layout():
    """
    Returns a Dash layout that matches the look of the provided screenshot:
    - Large welcome header
    - Hero card with three feature tiles
    - Recents card with a simple table
    """
    feature_tile = lambda title, desc, color: dbc.Card(
        dbc.CardBody([
            html.Div(style={
                "height": "92px",
                "borderRadius": "8px",
                "background": color,
                "marginBottom": "12px"
            }),
            html.H6(title, className="mb-2"),
            html.Small(desc, className="text-muted")
        ]),
        className="h-100 shadow-sm",
        style={"borderRadius": "10px"}
    )

    hero = dbc.Card(
        dbc.CardBody([
            html.H2("Welcome to Quick Suite", className="mb-3"),
            html.P("Explore the powerful new features of Quick Suite", className="lead text-muted"),
            dbc.Row(
                [
                    dbc.Col(feature_tile(
                        "Scenarios",
                        "Explore what-if questions, create in-depth analyses, and share actionable insights.",
                        "linear-gradient(90deg,#7c4dff,#c77dff)"
                    ), md=4),
                    dbc.Col(feature_tile(
                        "Enhanced dashboards",
                        "Generate insights from any dashboard using AI-powered chat.",
                        "linear-gradient(90deg,#6ec6ff,#8aa4ff)"
                    ), md=4),
                    dbc.Col(feature_tile(
                        "Analyses",
                        "Create insightful and dynamic visualizations by transforming your data.",
                        "linear-gradient(90deg,#ff8a80,#ffca8a)"
                    ), md=4)
                ],
                className="g-3 mt-2"
            )
        ]),
        className="mb-4",
        style={"borderRadius": "12px", "padding": "18px"}
    )

    # Simple "Recents" table that visually matches the screenshot structure
    recents_table = dbc.Table(
        # table head
        [html.Thead(html.Tr([
            html.Th("Name"),
            html.Th("Type"),
            html.Th("Last viewed", style={"textAlign": "right"})
        ])),

        # sample rows (replace with real data through callbacks/stores)
        bordered=False,
        hover=True,
        responsive=True,
        className="mt-2"
    )

    # sample body (replace with dynamic rows later)
    recents_body = [
        html.Tbody([
            html.Tr([
                html.Td("Disbursements & Overdues"),
                html.Td(html.Span("Dashboard", className="badge bg-light text-dark")),
                html.Td("17 days ago", style={"textAlign": "right"})
            ]),
            html.Tr([
                html.Td("Sales Overview"),
                html.Td(html.Span("Dashboard", className="badge bg-light text-dark")),
                html.Td("3 days ago", style={"textAlign": "right"})
            ])
        ])
    ]

    recents_card = dbc.Card(
        dbc.CardBody([
            html.H5("Recents", className="mb-3"),
            recents_table,  # placeholder table header
            *recents_body
        ]),
        className="shadow-sm",
        style={"borderRadius": "10px", "padding": "16px"}
    )

    container = dbc.Container(
        [
            hero,
            recents_card
        ],
        fluid=True,
        style={"paddingTop": "18px", "maxWidth": "1100px"}
    )

    return html.Div(container, style={"padding": "24px 28px"})