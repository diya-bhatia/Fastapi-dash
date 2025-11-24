import pandas as pd
import requests
from dash_svg import Svg, Path

def post_df(url, payload):
    """POST JSON payload and return DataFrame (or (None, error_msg))."""
    try:
        res = requests.post(url, json=payload, timeout=30)
        if not res.ok:
            try:
                detail = res.json().get("detail", res.text)
            except Exception:
                detail = res.text
            return None, f"{res.status_code}: {detail}"
        return pd.DataFrame(res.json()), None
    except Exception as e:
        return None, f"Request failed: {e}"

def get_json(url):
    try:
        res = requests.get(url, timeout=30)
        if not res.ok:
            try:
                detail = res.json().get("detail", res.text)
            except Exception:
                detail = res.text
            return None, f"{res.status_code}: {detail}"
        return res.json(), None
    except Exception as e:
        return None, f"Request failed: {e}"


# ---------- SVG helper using dash_svg ----------
def edit_svg_icon(color="#ffffff", size=14):
    """Return a dash_svg Svg pencil icon (small)."""
    # Simple pencil path (looks good at small sizes)
    return Svg([
        Path(d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z"),
        Path(d="M20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z")
    ],
    width=str(size),
    height=str(size),
    style={"verticalAlign":"middle", "display":"inline-block"},
    fill=color)