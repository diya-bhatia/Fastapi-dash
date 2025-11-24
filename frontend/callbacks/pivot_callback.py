from dash import Input, Output, State, html, ALL
import pandas as pd
from services.api_client import post_df
from config import PIVOT_URL
from services.api_client import edit_svg_icon  

def register_pivot_table_callbacks(app):

    @app.callback(
        Output("pivot-table", "children"),
        Output("last-pivot-data", "data"),
        Output("last-pivot-config", "data"),
        Output("last-pivot-html", "data"),  # store rendered pivot HTML
        Input("generate-table", "n_clicks"),
        Input("header_name_map_store","data"),
        Input({"type": "filter-col-table", "index": ALL}, "value"),
        Input({"type": "filter-val-table", "index": ALL}, "value"),
        State("table-dataset","value"),
        State("table-rows","value"),
        State("table-cols","value"),
        State("table-vals","value"),
        State("table-aggfunc","value"),
        State("calculated_fields_store","data"),
        prevent_initial_call=False
    )
    def generate_table(n_clicks, header_map, filter_cols, filter_vals, ds, rows, cols, vals, aggfunc, calc_store):
        if not ds:
            msg = html.Div("Select a dataset and click Generate Table.", className="text-muted")
            return msg, [], [], str(msg)

        calculated_fields = [{"name": f["name"], "formula": f["formula"]} for f in (calc_store or [])]

        # Prepare filters
        filters = []
        if filter_cols and filter_vals:
            for c, v in zip(filter_cols, filter_vals):
                if c and v:
                    filters.append({"column": c, "value": v})

        payload = {
            "dataset_id": ds,
            "rows": rows or [],
            "columns": cols or [],
            "values": vals or [],
            "aggfunc": aggfunc,
            "calculated_fields": calculated_fields,
            "filters": filters
        }

        df, err = post_df(PIVOT_URL, payload)
        if err or df is None or df.empty:
            msg = html.Div(f"No data found. {err or ''}", className="text-muted")
            return msg, [], [], str(msg)

        # Map headers
        header_map = header_map or {}
        display_cols = [header_map.get(c, c) for c in df.columns]

        # Build header
        header_style = {
            "backgroundColor": "#670178", "color": "white", "fontWeight": "bold",
            "textAlign": "center", "padding": "8px", "borderBottom": "2px solid #555",
            "borderRight": "1px solid #bbb", "position": "sticky", "top": "0", "zIndex": "3"
        }

        th_cells = []
        for orig_col, disp in zip(df.columns, display_cols):
            rename_btn = html.Button(
                edit_svg_icon(color="#ffffff", size=14),
                id={"type":"rename-btn","col":orig_col},
                n_clicks=0,
                title=f"Rename {orig_col}",
                style={"border":"none","background":"transparent","cursor":"pointer",
                       "padding":"0","marginLeft":"6px","display":"inline-flex","alignItems":"center"}
            )
            th_html = html.Div([html.Span(disp), rename_btn],
                               style={"display":"inline-flex","alignItems":"center","gap":"6px"})
            th_cells.append((orig_col, th_html))

        table_header = html.Tr(
            [html.Th(th_cells[0][1], style={**header_style, "left":"0","zIndex":"4"})] +
            [html.Th(h, style=header_style) for _, h in th_cells[1:]]
        )

        # Build rows
        n_row_dims = len(rows or [])
        table_rows = []
        total_row = None

        row_keys = []
        seen_parents = [{} for _ in range(n_row_dims)]
        for i, r in df.iterrows():
            labels = []
            for k in range(n_row_dims):
                val = "" if pd.isna(r.iloc[k]) else str(r.iloc[k])
                if not val:
                    val = seen_parents[k].get("value", "")
                else:
                    seen_parents[k]["value"] = val
                for deeper in range(k+1, n_row_dims):
                    seen_parents[deeper]["value"] = ""
                labels.append(val)
            full_key = "||".join(labels)
            parent_key = "||".join(labels[:-1]) if n_row_dims > 1 else ""
            row_keys.append((full_key, parent_key))

        children_map = {}
        for idx, (k, p) in enumerate(row_keys):
            children_map.setdefault(p, []).append(k)

        def cell_style(level=0, is_first=False, is_total=False):
            s = {
                "padding":"6px",
                "paddingLeft": f"{20*level + 6}px",
                "borderRight":"1px solid #ccc",
                "borderBottom":"1px solid #ccc",
                "whiteSpace":"nowrap",
                "overflow":"hidden",
                "textOverflow":"ellipsis",
                "backgroundColor":"white",
                "textAlign":"center"
            }
            if is_first:
                s.update({"position":"sticky","left":"0","zIndex":"2","backgroundColor":"white"})
            if is_total:
                s.update({"backgroundColor":"#670178","color":"white","fontWeight":"bold"})
            return s

        for i, r in df.iterrows():
            labels = ["" if pd.isna(r.iloc[k]) else str(r.iloc[k]) for k in range(min(n_row_dims, len(df.columns)))]
            full_key, parent_key = row_keys[i]
            first_val = labels[0].lower() if labels and labels[0] else ""
            is_total = "total" in first_val
            cells = []
            for j, col in enumerate(df.columns):
                is_first = j == 0
                style = cell_style(level=j if j < n_row_dims else 0, is_first=is_first, is_total=is_total)
                if is_first:
                    has_children = full_key in children_map and len(children_map[full_key]) > 0
                    if not is_total and has_children:
                        exp = html.Button("▶", id={"type":"expander","row_key":full_key}, n_clicks=0,
                                        title="Expand / Collapse",
                                        style={"border":"none","background":"none","cursor":"pointer",
                                               "marginRight":"6px","fontSize":"12px","lineHeight":"12px"})
                        cells.append(html.Td([exp, r[col]], style=style))
                    else:
                        spacer = html.Span(style={"display":"inline-block","width":"16px","height":"12px","marginRight":"6px"})
                        cells.append(html.Td([spacer, r[col]], style=style))
                else:
                    cells.append(html.Td(r[col], style=style))
            tr = html.Tr(cells, **{"data-key": full_key, "data-parent-key": parent_key, "className":"pivot-row"})
            if is_total:
                total_row = tr
            else:
                table_rows.append(tr)
        if total_row:
            table_rows.append(total_row)

        # JS expand/collapse
        script = html.Script(f"""
        (function(){{
            setTimeout(() => {{
                const rows = Array.from(document.querySelectorAll("tr.pivot-row"));
                const childrenMap = new Map();
                rows.forEach(r => {{
                    const key = r.getAttribute('data-key') || '';
                    const parent = r.getAttribute('data-parent-key') || '';
                    if (!childrenMap.has(parent)) childrenMap.set(parent, []);
                    childrenMap.get(parent).push(key);
                }});
                const rowByKey = new Map();
                rows.forEach(r => rowByKey.set(r.getAttribute('data-key') || '', r));
                function hideDescendantsIterative(rootKey) {{
                    const stack = (childrenMap.get(rootKey) || []).slice();
                    while (stack.length) {{
                        const childKey = stack.pop();
                        const childRow = rowByKey.get(childKey);
                        if (!childRow) continue;
                        childRow.style.display = 'none';
                        const childBtn = childRow.querySelector("button[id*='expander']");
                        if (childBtn) childBtn.innerText = "▶";
                        const grandchildren = childrenMap.get(childKey) || [];
                        for (let g of grandchildren) stack.push(g);
                    }}
                }}
                function showDirectChildren(rootKey) {{
                    const direct = childrenMap.get(rootKey) || [];
                    for (let k of direct) {{
                        const r = rowByKey.get(k);
                        if (r) r.style.display = '';
                    }}
                }}
                rows.forEach(r => {{
                    const parent = r.getAttribute('data-parent-key') || '';
                    if (parent) r.style.display = 'none';
                }});
                document.querySelectorAll("button[id*='expander']").forEach(btn => {{
                    btn.addEventListener("click", (ev) => {{
                        ev.stopPropagation();
                        const tr = btn.closest('tr');
                        if (!tr) return;
                        const key = tr.getAttribute('data-key') || '';
                        const expanding = btn.innerText === "▶";
                        btn.innerText = expanding ? "▼" : "▶";
                        if (expanding) showDirectChildren(key); else hideDescendantsIterative(key);
                    }});
                }});
            }}, 100);
        }})();
        """)

        pivot_div = html.Div([html.Table([html.Thead(table_header), html.Tbody(table_rows)], style={"width":"100%","borderCollapse":"collapse","tableLayout":"fixed"}), script], 
                             style={"overflowX":"auto","maxHeight":"100%","border":"1px solid #ccc","borderRadius":"6px","backgroundColor":"white"})

        # Convert Dash component to HTML string for publishing
        pivot_html_str = str(pivot_div)

        return pivot_div, df.to_dict("records"), payload, pivot_html_str
