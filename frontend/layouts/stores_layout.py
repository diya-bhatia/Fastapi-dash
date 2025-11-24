from dash import dcc

def stores_layout():
    return [
        dcc.Store(id="columns_store", data=[]),
        dcc.Store(id="datasets_refresh_store", data=0),
        dcc.Store(id="calculated_fields_store", data=[]),
        dcc.Store(id="calculated_fields_chart_store", data=[]),
        dcc.Store(id="header_name_map_store", data={}),
        dcc.Store(id="rename-target", data=None),
        dcc.Store(id="collapsed_store", data={}),
        dcc.Store(id="filters-store", data=[]),
        dcc.Store(id="last-pivot-data", data=[]),
        dcc.Store(id="last-pivot-config", data=[]),
        dcc.Store(id="last-pivot-html", data=None),
    ]
