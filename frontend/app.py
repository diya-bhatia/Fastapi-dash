# # app.py
# import dash
# import dash_html_components as html
# import dash_core_components as dcc
# from dash.dependencies import Input, Output
# from components.left_panel import get_left_panel
# import requests

# app = dash.Dash(__name__)
# app.title = "Quick Suite"

# def get_screen_content(page_name):
#     # Replace with actual API endpoints for different screens
#     api_mapping = {
#         "home": "http://localhost:8000/v1/home",
#         "favorites": "http://localhost:8000/v1/favorites",
#         "analyses": "http://localhost:8000/v1/analyses",
#         "dashboards": "http://localhost:8000/v1/dashboards",
#         # Add more as needed
#     }
#     endpoint = api_mapping.get(page_name.lower())
#     if endpoint:
#         resp = requests.get(endpoint)
#         data = resp.json()
#         return html.Div([html.H3(f"{page_name.capitalize()} screen"), html.Pre(str(data))])
#     return html.Div([html.H3("Screen not found")])

# app.layout = html.Div([
#     html.Div(get_left_panel(), style={"float": "left"}),
#     html.Div(id="main-content", style={"marginLeft": "220px", "padding": "40px"})
# ])

# @app.callback(
#     Output("main-content", "children"),
#     [
#         Input("nav-home", "n_clicks"),
#         Input("nav-favorites", "n_clicks"),
#         Input("nav-analyses", "n_clicks"),
#         Input("nav-dashboards", "n_clicks"),
#         Input("nav-stories", "n_clicks"),
#         Input("nav-topics", "n_clicks"),
#         Input("nav-datasets", "n_clicks"),
#         Input("nav-myfolders", "n_clicks"),
#         Input("nav-sharedfolders", "n_clicks"),
#     ]
# )
# def update_screen(*btns):
#     btn_names = [
#         "home", "favorites", "analyses", "dashboards",
#         "stories", "topics", "datasets", "myfolders", "sharedfolders"
#     ]
#     # Find which button was clicked most recently
#     clicked = [i for i, v in enumerate(btns) if v and v > 0]
#     if clicked:
#         active = btn_names[clicked[-1]]
#         return get_screen_content(active)
#     # Default screen
#     return get_screen_content("home")

# if __name__ == "__main__":
#     app.run(debug=True, port=8050)


# # # app.py

# # import dash
# # import dash_bootstrap_components as dbc
# # from dash import html, dcc

# # from components.left_panel import build_left_panel
# # from layouts.main_layout import main_layout
# # from callbacks import register_all_callbacks
# # from callbacks.routing_callbacks import register_routing_callbacks
# # from callbacks import navigation  # registers display_page

# # # ---- Initialize Dash app ----
# # app = dash.Dash(
# #     __name__,
# #     external_stylesheets=[dbc.themes.BOOTSTRAP],
# #     suppress_callback_exceptions=True  # Needed for dynamic callbacks
# # )

# # # ---- Build Sidebar ----
# # left_panel = build_left_panel()

# # # ---- App Layout ----
# # app.layout = html.Div([
# #     # Multi-page support
# #     dcc.Location(id="url"),
# #     html.Div(id="page-content"),

# #     # Client-side stores
# #     dcc.Store(id="columns_store", data={}),
# #     dcc.Store(id="last-pivot-config", data={}),
# #     dcc.Store(id="last-pivot-data", data={}),
# #     dcc.Store(id="calculated_fields_store", data={}),
# #     dcc.Store(id="calculated_fields_chart_store", data={}),

# #     # Hidden placeholders for dynamic components
# #     html.Div(id="rename-cancel", style={"display": "none"}),
# #     html.Div(id="rename-save", style={"display": "none"}),
# #     html.Div(id="add-calc-field-chart", style={"display": "none"}),
# #     html.Div(id="add-calc-field-table", style={"display": "none"})
# # ])

# # # ---- Register Callbacks ----
# # register_all_callbacks(app)                  # Your main callbacks
# # register_routing_callbacks(app, left_panel)  # Routing callbacks

# # # ---- Run App ----
# # if __name__ == "__main__":
# #     app.run(debug=True, port=8050)


# app.py
import dash
from dash import html,dcc
from dash.dependencies import Input, Output,State
from components.left_panel import get_left_panel
import requests
from dash import callback_context

app = dash.Dash(__name__)
app.title = "Quick Suite"

# Mapping button to API endpoint
api_mapping = {
    "home": "http://localhost:8000/v1/home",
    "favorites": "http://localhost:8000/v1/favorites",
    "analyses": "http://localhost:8000/v1/analyses",
    "dashboards": "http://localhost:8000/v1/dashboards",
    "stories": "http://localhost:8000/v1/stories",
    "topics": "http://localhost:8000/v1/topics",
    "datasets": "http://localhost:8000/v1/datasets",
    "myfolders": "http://localhost:8000/v1/myfolders",
    "sharedfolders": "http://localhost:8000/v1/sharedfolders",
}

def get_home_ui():
    # Main landing page, as in your image
    cards = [
        html.Div([
            html.Div("Scenarios", className="card-title"),
            html.P("Explore what-if questions, create in-depth analyses, and share actionable insights from your data with the help of AI assistants.", className="card-desc"),
        ], className="feature-card"),
        html.Div([
            html.Div("Enhanced dashboards", className="card-title"),
            html.P("Generate insights from any dashboard using AI-powered chat.", className="card-desc"),
        ], className="feature-card"),
        html.Div([
            html.Div("Analyses", className="card-title"),
            html.P("Create insightful and dynamic visualizations by transforming your data into interactive dashboards.", className="card-desc"),
        ], className="feature-card"),
    ]
    return html.Div([
        html.H2("Welcome to Quick Suite", className="main-title"),
        html.Div(cards, className="features-row"),
        html.Div([
            html.H3("Recents", className="recents-title"),
            html.Div([
                html.Div([
                    html.Div("Disbursements & Overdues", className="recent-name"),
                    html.Div("Dashboard", className="recent-type"),
                    html.Div("17 days ago", className="recent-viewed"),
                ], className="recent-row"),
            ], className="recents-section"),
        ], className="recents-wrapper"),
    ], className="main-content")


def get_favorites_ui():
    return html.Div([
        html.H2("Favorites", className="main-title", style={"marginBottom": "38px"}),
        html.Div([
            html.Div([
                # Replace src below with your real SVG or image path for the illustration
                html.Img(src="/assets/favorites_icon.svg", style={"width": "110px", "marginBottom": "22px"}),
                html.Div(
                    "Favorite the Quick Suite resources you use the most to view them here.",
                    className="fav-desc",
                    style={
                        "fontSize": "18px",
                        "color": "#444",
                        "marginBottom": "30px"
                    }
                ),
                html.Div([
                    html.Button("Go to analyses", id="go-analyses", className="fav-btn"),
                    html.Button("Go to dashboards", id="go-dashboards", className="fav-btn", style={"marginLeft": "18px"}),
                ], style={"display": "flex", "justifyContent": "center"}),
            ], style={"display": "flex", "flexDirection": "column", "alignItems": "center", "padding": "55px 0"})
        ],
        className="favorites-card",
        style={
            "background": "white",
            "borderRadius": "20px",
            "boxShadow": "0 2px 14px rgba(160,110,240, 0.09)",
            "width": "82%",
            "margin": "auto",
            "marginTop": "40px",
            "marginBottom": "24px",
            "minHeight": "360px",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center"
        }),
    ], className="main-content")


def get_analyses_ui():
    return html.Div([
        html.H2("Analyses", className="main-title", style={"marginBottom": "38px"}),
        html.Div([
            html.Div([
                html.Div("Create insightful and interactive visualizations", className="analyses-feature-title"),
                html.Div(
                    "Transform your data into dynamic charts and graphs with intuitive analysis tools. Share your completed analyses as interactive dashboards or multi-page reports.",
                    className="analyses-feature-desc",
                    style={"marginBottom": "28px"}
                ),
                html.Div([
                    html.Button("Create analysis", id="create-analysis", className="analyses-btn"),
                    html.Button("Dismiss", id="dismiss-analysis", className="analyses-btn", style={"marginLeft": "16px", "background": "white", "color": "#8967e7", "border": "1.8px solid #ded6fe"}),
                ], style={"display": "flex", "alignItems": "center"}),
            ],
            style={"padding": "34px 36px 28px 42px", "maxWidth": "650px"}),
            # Replace the src below with your actual analytics chart image
            html.Img(src="/assets/analyses_header.svg", style={"height": "180px", "marginLeft": "auto", "marginBottom": "10px"}),
        ],
        className="analyses-feature-card",
        style={
            "background": "linear-gradient(90deg,#7944e7 47%,#d7aefa 100%)",
            "borderRadius": "18px",
            "boxShadow": "0 4px 16px rgba(110,60,220,0.17)",
            "width": "93%",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "margin": "auto",
            "marginBottom": "35px"
        }),
        html.Div([
            html.Div([
                html.Img(src="/assets/favorites_icon.svg", style={"width": "110px", "marginBottom": "22px"}),
                html.Div(
                    "Create your first analysis and find it here.",
                    style={"fontSize": "16px", "color": "#4a348f", "marginBottom": "16px", "marginTop": "8px"}
                ),
                html.Button("Create analysis", id="create-analysis-bottom", className="analyses-btn"),
            ], style={"display": "flex", "flexDirection": "column", "alignItems": "center", "padding": "55px 0"})
        ],
        className="analyses-empty-card",
        style={
            "background": "white",
            "borderRadius": "20px",
            "boxShadow": "0 2px 14px rgba(160,110,240, 0.09)",
            "width": "82%",
            "margin": "auto",
            "marginTop": "40px",
            "marginBottom": "24px",
            "minHeight": "340px",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center"
        }),
    ], className="main-content")


def get_dashboards_ui(dashboard_items=None):
    # dashboard_items: list of dicts with keys: name, owner, last_updated, etc.
    has_items = dashboard_items and len(dashboard_items) > 0
    table_header = html.Div([
        html.Div("Name", className="dashboard-header-cell", style={"flex": "2"}),
        html.Div("Owner", className="dashboard-header-cell", style={"flex": "1"}),
        html.Div("Last Updated", className="dashboard-header-cell", style={"flex": "1"}),
        html.Div("Action", className="dashboard-header-cell", style={"flex": "0.6"}),
    ], className="dashboard-table-header", style={"display": "flex", "padding": "18px 12px","fontWeight":"bold","fontSize":"17px"})
    
    item_rows = [
        html.Div([
            html.Div([
                html.I(className="fa fa-star-o", style={"color":"#8756e7","marginRight":"8px"}),
                html.Span(item["name"], style={"color":"#453088"}),
            ], style={"flex": "2"}),
            html.Div(item.get("owner", "Me"), style={"flex": "1"}),
            html.Div(item.get("last_updated", "--"), style={"flex": "1"}),
            html.Div("...", style={"flex": "0.6", "textAlign": "center"}),
        ], className="dashboard-table-row", style={"display": "flex", "padding": "16px 12px","fontSize":"16px","color":"#4e4098"})
        for item in dashboard_items or []
    ]
    
    dashboard_table = html.Div([
        table_header,
        html.Div(item_rows)
    ], className="dashboard-table")

    empty_card = html.Div([
        html.Div([
            html.Img(src="/assets/favorites_icon.svg", style={"width": "110px", "marginBottom": "22px"}),
            html.Div(
                "Create your first dashboard and find it here.",
                style={"fontSize": "16px", "color": "#4a348f", "marginBottom": "16px", "marginTop": "8px"}
            ),
            html.Button("Create dashboard", id="create-dashboard-btn", className="analyses-btn"),
        ], style={"display": "flex", "flexDirection": "column", "alignItems": "center", "padding": "55px 0"})
    ],
    style={
        "background": "white",
        "borderRadius": "20px",
        "boxShadow": "0 2px 14px rgba(160,110,240, 0.09)",
        "width": "82%",
        "margin": "auto",
        "marginTop": "40px",
        "marginBottom": "24px",
        "minHeight": "340px",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center"
    })

    return html.Div([
        html.H2("Dashboards", className="main-title", style={"marginBottom": "38px"}),
        html.Div(
            dashboard_table if has_items else empty_card,
            className="dashboard-card",
            style={
                "background": "white",
                "borderRadius": "20px",
                "boxShadow": "0 2px 14px rgba(160,110,240, 0.09)",
                "width": "98%",
                "margin": "auto",
                "marginTop": "40px",
                "marginBottom": "24px",
                "minHeight": "340px"
            })
    ], className="main-content")

def get_dashboard_data():
    # Replace with API call or actual backend fetch for real data
    # Return [] for empty, or sample for demo
    # return []
    return [{
        "name":"Disbursements & Overdues",
        "owner":"Me",
        "last_updated":"a month ago"
    }]


def get_stories_ui():
    # Top info bar ("Upgrade user roles to create stories")
    info_bar = html.Div([
        html.Div([
            html.I(className="fa fa-info-circle", style={"color": "#54a4e6", "marginRight": "8px"}),
            html.Span("Upgrade user roles to create stories", style={"fontWeight": "600", "fontSize": "15px"}),
            html.Span("Dismiss", id="dismiss-stories-info", style={"float": "right", "fontWeight": 500, "color": "#4e4098", "cursor": "pointer", "marginLeft": "20px"}),
            html.I(className="fa fa-times", style={"float": "right", "marginLeft": "7px", "cursor": "pointer", "color": "#623ba7"})
        ], style={"display": "flex", "alignItems": "center", "justifyContent": "space-between"})
    ], style={
        "background": "#ecf7ff",
        "borderRadius": "7px",
        "padding": "18px 24px",
        "marginBottom": "25px",
        "marginTop": "0",
        "fontSize": "15px",
        "border": "1.2px solid #c2e0fd"
    })

    # Main feature card below info bar
    main_card = html.Div([
        html.Div([
            html.Div("Share insights with stories", className="stories-feature-title"),
            html.Div(
                "Use stories to effectively communicate data narratives with stakeholders and drive informed business decisions",
                className="stories-feature-desc",
                style={"marginBottom": "18px"}
            ),
            html.Div([
                html.Button("Learn more", id="learn-more-story", className="analyses-btn"),
                html.Button("Dismiss", id="dismiss-story-main", className="analyses-btn", style={"marginLeft": "16px", "background": "white", "color": "#8967e7", "border": "1.8px solid #ded6fe"}),
            ], style={"display": "flex", "alignItems": "center"}),
        ],
        style={"padding": "34px 36px 28px 42px", "minWidth": "330px"}),
        # Replace with your story illustration
        html.Img(src="/assets/stories_header.svg", style={"height": "162px", "marginLeft": "auto", "marginBottom": "10px"}),
    ],
    className="stories-feature-card",
    style={
        "background": "linear-gradient(90deg,#7944e7 50%,#d7aefa 100%)",
        "borderRadius": "18px",
        "boxShadow": "0 4px 16px rgba(110,60,220,0.15)",
        "width": "93%",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "space-between",
        "margin": "auto",
        "marginBottom": "35px"
    })

    # Empty state card
    empty_card = html.Div([
        html.Div([
            html.Img(src="/assets/favorites_icon.svg", style={"width": "110px", "marginBottom": "22px"}),
            html.Div(
                "No stories shared with you yet.",
                style={"fontSize": "16px", "color": "#666", "marginBottom": "8px", "marginTop": "8px"}
            ),
        ], style={"display": "flex", "flexDirection": "column", "alignItems": "center", "padding": "55px 0"})
    ],
    style={
        "background": "white",
        "borderRadius": "20px",
        "boxShadow": "0 2px 14px rgba(160,110,240, 0.09)",
        "width": "82%",
        "margin": "auto",
        "marginTop": "40px",
        "marginBottom": "24px",
        "minHeight": "340px",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center"
    })

    return html.Div([
        html.H2("Stories", className="main-title", style={"marginBottom": "18px"}),
        info_bar,
        main_card,
        empty_card
    ], className="main-content")


def get_topics_ui():
    # Info alert at top
    info_bar = html.Div([
        html.Div([
            html.I(className="fa fa-info-circle", style={"color": "#54a4e6", "marginRight": "8px"}),
            html.Span("Upgrade user roles to create topics", style={"fontWeight": "600", "fontSize": "15px"}),
            html.Span("Dismiss", id="dismiss-topics-info", style={"float": "right", "fontWeight": 500, "color": "#4e4098", "cursor": "pointer", "marginLeft": "20px"}),
            html.I(className="fa fa-times", style={"float": "right", "marginLeft": "7px", "cursor": "pointer", "color": "#623ba7"})
        ], style={"display": "flex", "alignItems": "center", "justifyContent": "space-between"})
    ], style={
        "background": "#ecf7ff",
        "borderRadius": "7px",
        "padding": "17px 22px",
        "marginBottom": "25px",
        "fontSize": "15px",
        "border": "1.2px solid #c2e0fd"
    })

    # Feature card
    main_card = html.Div([
        html.Div([
            html.Div("Define your data's context to improve AI accuracy", className="topics-feature-title"),
            html.Div(
                "Enable more accurate and relevant insights by creating topics that establish your business context and domain-specific terminology. Help users get relevant answers through natural language queries. ",
                className="topics-feature-desc",
                style={"marginBottom": "18px"}
            ),
            html.Div([
                html.Button("Create topic", id="create-topic", className="analyses-btn"),
                html.Button("Dismiss", id="dismiss-topic-main", className="analyses-btn", style={"marginLeft": "16px", "background": "white", "color": "#8967e7", "border": "1.8px solid #ded6fe"}),
            ], style={"display": "flex", "alignItems": "center"}),
            html.A("Learn more", href="#", style={"color":"#fff","fontSize":"15px","textDecoration":"underline","marginTop":"10px"}),
        ],
        style={"padding": "34px 36px 28px 42px", "minWidth": "330px"}),
        # Replace with your analytics image
        html.Img(src="/assets/topics_header.svg", style={"height": "155px", "marginLeft": "auto", "marginBottom": "10px"}),
    ],
    className="topics-feature-card",
    style={
        "background": "linear-gradient(90deg,#7944e7 60%,#ee29b2 100%)",
        "borderRadius": "18px",
        "boxShadow": "0 4px 16px rgba(110,60,220,0.15)",
        "width": "93%",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "space-between",
        "margin": "auto",
        "marginBottom": "35px"
    })

    # Empty state card
    empty_card = html.Div([
        html.Div([
            html.Img(src="/assets/favorites_icon.svg", style={"width": "110px", "marginBottom": "22px"}),
            html.Div(
                "Create your first topic or sample topic and find it here.",
                style={"fontSize": "16px", "color": "#666", "marginBottom": "8px", "marginTop": "8px"}
            ),
        ], style={"display": "flex", "flexDirection": "column", "alignItems": "center", "padding": "55px 0"})
    ],
    style={
        "background": "white",
        "borderRadius": "20px",
        "boxShadow": "0 2px 14px rgba(160,110,240, 0.09)",
        "width": "82%",
        "margin": "auto",
        "marginTop": "40px",
        "marginBottom": "24px",
        "minHeight": "340px",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center"
    })

    return html.Div([
        html.H2("Topics", className="main-title", style={"marginBottom": "18px"}),
        info_bar,
        main_card,
        empty_card
    ], className="main-content")


def get_datasets_ui(dataset_items=None):
    # Tab headers (Datasets / Data sources)
    tab_header = html.Div([
        html.Button("Datasets", id="datasets-tab-btn", className="datasets-tab-active"),
        html.Button("Data sources", id="datasources-tab-btn", className="datasets-tab"),
    ], style={"display": "flex", "gap": "15px", "marginBottom": "24px", "marginTop": "15px"})

    # Check if there are dataset items
    has_items = dataset_items and len(dataset_items) > 0

    # If datasets available
    if has_items:
        dataset_rows = [
            html.Div([
                html.Div(item["name"], style={"flex": "2"}),
                html.Div(item.get("created_by", "Me"), style={"flex": "1"}),
                html.Div(item.get("last_updated", "--"), style={"flex": "1"}),
                html.Div("...", style={"flex": "0.6", "textAlign": "center"}),
            ], style={"display": "flex", "padding": "16px 12px","fontSize":"16px","color":"#4e4098",
                    "borderBottom": "1px solid #f0eafc"})
            for item in dataset_items
        ]
        datasets_table = html.Div([
            tab_header,
            html.Div([
                html.Div([
                    html.Div("Name", style={"flex": "2", "fontWeight": "bold", "color": "#8567e7"}),
                    html.Div("Created By", style={"flex": "1", "fontWeight": "bold", "color": "#8567e7"}),
                    html.Div("Last Updated", style={"flex": "1", "fontWeight": "bold", "color": "#8567e7"}),
                    html.Div("Action", style={"flex": "0.6", "fontWeight": "bold", "color": "#8567e7"}),
                ], style={"display": "flex", "padding": "18px 12px","fontSize":"17px", "background": "#f7f2ff", "borderBottom": "1.5px solid #e2d9f9"}),
                html.Div(dataset_rows)
            ])
        ])
    else:
        # Empty dataset state
        datasets_table = html.Div([
            tab_header,
            html.Div([
                html.Img(src="/assets/favorites_icon.svg", style={"width": "110px", "marginBottom": "22px"}),
                html.Div(
                    "Create your first dataset and find it here.",
                    style={"fontSize": "16px", "color": "#4a348f", "marginBottom": "10px", "marginTop": "8px"}
                ),
                html.Button("Create dataset", id="create-dataset-btn", className="analyses-btn"),
            ], style={"display": "flex", "flexDirection": "column", "alignItems": "center", "padding": "55px 0"})
        ])

    return html.Div([
        html.H2("Datasets", className="main-title", style={"marginBottom": "38px"}),
        html.Div(
            datasets_table,
            style={
                "background": "white",
                "borderRadius": "20px",
                "boxShadow": "0 2px 14px rgba(160,110,240, 0.09)",
                "width": "98%",
                "margin": "auto",
                "marginTop": "40px",
                "marginBottom": "24px",
                "minHeight": "350px"
            }
        )
    ], className="main-content")

def get_dataset_data():
    # Simulate with fake data or fetch from API
    # Return empty list for empty state, or sample list
    # return []
    return [{
        "name": "Customer Orders",
        "created_by": "Me",
        "last_updated": "10 days ago"
    }]


# def get_myfolders_ui(folders=None):
#     # Header button
#     new_folder_btn = html.Button("New Folder", id="new-folder-btn", style={
#         "background": "#4d0b94", "color": "#fff", "borderRadius": "7px", "padding":"8px 22px",
#         "position":"absolute", "right":"50px", "top":"22px", "fontWeight":"600", "fontSize":"16px", "border":"none"
#     })

#     # List folders
#     folders_section = []
#     if folders and len(folders) > 0:
#         for folder_name in folders:
#             folders_section.append(html.Div([
#                 html.I(className="fa fa-folder-open", style={"color":"#694bbf","fontSize":"27px","marginRight":"16px"}),
#                 html.Span(folder_name, style={"fontSize":"18px", "fontWeight":"600", "color":"#363636"}),
#             ], style={"display":"flex", "alignItems":"center", "margin":"12px 0"}))
#     else:
#         folders_section = html.Div([
#             html.I(className="fa fa-folder-open", style={"color":"#B8B8B8", "fontSize":"40px"}),
#             html.Div("No personal folders", style={"fontSize":"20px", "color":"#727272", "marginTop":"16px", "fontWeight":"500"}),
#             html.Div("Keep all your analyses, dashboards, and data neat and tidy.", style={"color":"#B8B8B8", "fontSize":"15px", "marginTop":"10px"})
#         ], style={"textAlign":"center","marginTop":"60px"})

#     return html.Div([
#         html.Div([
#             html.H3("My folders", style={"paddingTop":"18px", "paddingLeft":"16px", "marginBottom":"12px"}),
#             new_folder_btn
#         ], style={"position":"relative"}),
#         html.Div(folders_section, id="folders-list", style={"marginTop":"90px", "paddingLeft":"24px"}),
#         dcc.Store(id="myfolders-store", storage_type="session"),  # stores folder names for this user/session
#         dcc.Input(id="new-folder-input", type="text", placeholder="Enter folder name",
#                   style={"display":"none", "position":"absolute", "right":"210px", "top":"26px"})
#     ], className="main-content")


def get_api_page_ui(page_name):
    endpoint = api_mapping.get(page_name)
    if not endpoint:
        return html.Div([
            html.H3("Screen not found", className="main-title"),
            html.P("No API configured for this page.", className="card-desc")
        ], className="main-content")
    try:
        resp = requests.get(endpoint)
        resp.raise_for_status()
        data = resp.json()
        # You can customize layout below per section; here's a simple card for API data
        return html.Div([
            html.H2(f"{page_name.capitalize()}", className="main-title"),
            html.Div([
                html.Pre(str(data), className="api-data")
            ], className="feature-card"),
        ], className="main-content")
    except Exception as e:
        return html.Div([
            html.H3(f"{page_name.capitalize()}", className="main-title"),
            html.Div([
                html.P(f"Error fetching data: {str(e)}", className="card-desc")
            ], className="feature-card")
        ], className="main-content")


# @app.callback(
#     [Output("myfolders-store", "data"),
#      Output("new-folder-input", "style")],
#     [Input("new-folder-btn", "n_clicks"),
#      Input("new-folder-input", "n_submit")],
#     [State("myfolders-store", "data"),
#      State("new-folder-input", "value")]
# )
# def manage_new_folder(btn_click, submit, folders_data, folder_name):
#     ctx = callback_context
#     folders = folders_data or []
#     # Click to show input
#     if ctx.triggered and "new-folder-btn" in ctx.triggered[0]['prop_id']:
#         return folders, {"display":"inline-block","position":"absolute","right":"210px","top":"26px"}
#     # Submit to add folder
#     if ctx.triggered and "new-folder-input" in ctx.triggered[0]['prop_id'] and folder_name:
#         folders.append(folder_name)
#         return folders, {"display":"none"}
#     return folders, {"display":"none"}


app.layout = html.Div([
    get_left_panel(),
    html.Div(id="main-content", className="main-area"),
])

@app.callback(
    Output("main-content", "children"),
    [Input(f"nav-{name}", "n_clicks") for name in [
        "home", "favorites", "analyses", "dashboards", "stories",
        "topics", "datasets", "myfolders", "sharedfolders"
    ]],
)
    # [Input("myfolders-store", "data")],
def update_screen(*btns_and_data):
    btns = btns_and_data[:-1]
    folders_data = btns_and_data[-1] or []  # list of folder names if any

    btn_names = [
        "home", "favorites", "analyses", "dashboards",
        "stories", "topics", "datasets", "myfolders", "sharedfolders"
    ]
    clicked = [i for i, v in enumerate(btns) if v and v > 0]
    active = btn_names[clicked[-1]] if clicked else "home"
    if active == "home":
        return get_home_ui()
    elif active == "favorites":
        return get_favorites_ui()
    elif active == "analyses":
        return get_analyses_ui()
    elif active == "dashboards":
        return get_dashboards_ui(get_dashboard_data())
    elif active == "stories":
        return get_stories_ui()
    elif active == "topics":
        return get_topics_ui()
    elif active == "datasets":
        return get_datasets_ui(get_dataset_data())
    # elif active == "myfolders":
    #     return get_myfolders_ui(folders=folders_data)
    else:
        return get_api_page_ui(active)

if __name__ == "__main__":
    app.run(debug=True)
