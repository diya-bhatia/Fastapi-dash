# main.py
import os
import uuid
import re
from io import BytesIO
from typing import List , Union, Dict
import pandas as pd
import numpy as np
import boto3
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from redis_client import redis_client
import redis
from typing import Any, Dict



app = FastAPI()

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# Allow Dash frontend to call FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
DATASETS = {}
DATASET_META = {}
ACTIVE_DATASET_ID = None

# -----------------------------
# Request Models
# -----------------------------
class S3Source(BaseModel):
    bucket: str
    key: str

class DatasetRequest(BaseModel):
    name: str
    source_type: str          # "s3" or "local"
    file_format: str          # parquet | csv
    s3: S3Source | None = None
    local_path: str | None = None

class CalculatedField(BaseModel):
    name: str
    formula: str

class FilterItem(BaseModel):
    column: str

class PivotRequest(BaseModel):
    rows: List[str] = []
    columns: List[str] = []
    values: List[str] = []
    aggfunc: Union[str, Dict[str, str]] = "sum"
    calculated_fields: List[CalculatedField] = []
    filters: List[FilterItem] = []

# ---------- Payload model ----------
class ReportPayload(BaseModel):
    report_config: Dict[str, Any]
    report_data: Any  # JSON-serializable (list of dicts)




# -----------------------------
# Helpers: Loading datasets
# -----------------------------
def load_dataset_from_source(req: DatasetRequest) -> pd.DataFrame:
    if req.source_type == "s3":
        s3 = boto3.client("s3")
        try:
            obj = s3.get_object(Bucket=req.s3.bucket, Key=req.s3.key)
            body = obj["Body"].read()
        except Exception as e:
            raise HTTPException(400, f"Failed to read S3 object: {e}")
        if req.file_format.lower() == "parquet":
            return pd.read_parquet(BytesIO(body))
        else:
            return pd.read_csv(BytesIO(body))
    elif req.source_type == "local":
        if not req.local_path or not os.path.exists(req.local_path):
            raise HTTPException(400, "Local file not found")
        if req.file_format.lower() == "parquet":
            return pd.read_parquet(req.local_path)
        else:
            return pd.read_csv(req.local_path)
    raise HTTPException(400, "Invalid source_type or file_format")


# -----------------------------
# QuickSight -> Pandas expression engine
# -----------------------------
_re_field = re.compile(r"\{(.*?)\}")
_token_re = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

def is_numeric_dtype(dtype):
    return np.issubdtype(dtype, np.number)

def _replace_field_tokens(expr: str):
    return _re_field.sub(lambda m: f'df["{m.group(1)}"]', expr)

def _split_args(s: str):
    parts = []
    current = []
    depth = 0
    in_quote = False
    quote_char = None
    i = 0
    while i < len(s):
        ch = s[i]
        if in_quote:
            current.append(ch)
            if ch == quote_char:
                in_quote = False
                quote_char = None
        else:
            if ch in ("'", '"'):
                in_quote = True
                quote_char = ch
                current.append(ch)
            elif ch == "(":
                depth += 1
                current.append(ch)
            elif ch == ")":
                depth -= 1
                current.append(ch)
            elif ch == "," and depth == 0:
                part = "".join(current).strip()
                if part:
                    parts.append(part)
                current = []
            else:
                current.append(ch)
        i += 1
    last = "".join(current).strip()
    if last:
        parts.append(last)
    return parts

def _translate_functions(expr: str, df: pd.DataFrame, valid_fields: set):
    src = expr
    src = re.sub(r"(?i)\bifelse\s*\(", "np.where(", src)
    src = re.sub(r"(?i)\bisnull\s*\(", "pd.isnull(", src)
    src = re.sub(r"(?i)\bisnotnull\s*\(", "pd.notnull(", src)

    def _coalesce_repl(match):
        inside = match.group(1)
        parts = [p.strip() for p in _split_args(inside)]
        expr = parts[0]
        for p in parts[1:]:
            expr = f"({expr}).fillna({p})"
        return expr
    src = re.sub(r"(?i)\bcoalesce\s*\((.*?)\)", _coalesce_repl, src, flags=re.DOTALL)

    src = re.sub(r"(?i)\babs\s*\(", "np.abs(", src)
    src = re.sub(r"(?i)\bceil\s*\(", "np.ceil(", src)
    src = re.sub(r"(?i)\bfloor\s*\(", "np.floor(", src)
    src = re.sub(r"(?i)\bround\s*\(", "np.round(", src)
    src = re.sub(r"(?i)\bln\s*\(", "np.log(", src)
    src = re.sub(r"(?i)\bpow\s*\(", "np.power(", src)

    # String
    src = re.sub(r"(?i)\bupper\s*\(\s*(df\[[^\]]+\])\s*\)", r"\1.str.upper()", src)
    src = re.sub(r"(?i)\blower\s*\(\s*(df\[[^\]]+\])\s*\)", r"\1.str.lower()", src)
    src = re.sub(r"(?i)\btrim\s*\(\s*(df\[[^\]]+\])\s*\)", r"\1.str.strip()", src)
    src = re.sub(r"(?i)\blen\s*\(\s*(df\[[^\]]+\])\s*\)", r"\1.str.len()", src)
    src = re.sub(r"(?i)\bcontains\s*\(\s*(df\[[^\]]+\])\s*,\s*([^,\)]+)\s*\)", r"\1.str.contains(\2)", src)
    src = re.sub(r"(?i)\bstartswith\s*\(\s*(df\[[^\]]+\])\s*,\s*([^,\)]+)\s*\)", r"\1.str.startswith(\2)", src)
    src = re.sub(r"(?i)\bendswith\s*\(\s*(df\[[^\]]+\])\s*,\s*([^,\)]+)\s*\)", r"\1.str.endswith(\2)", src)
    src = re.sub(r"(?i)\breplace\s*\(\s*(df\[[^\]]+\])\s*,\s*([^,\)]+)\s*,\s*([^,\)]+)\s*\)", r"\1.str.replace(\2,\3)", src)

    def _concat_repl(m):
        inner = m.group(1)
        parts = [p.strip() for p in _split_args(inner)]
        conv = [f"({p}).astype(str)" for p in parts]
        return " + ".join(conv)
    src = re.sub(r"(?i)\bconcat\s*\((.*?)\)", _concat_repl, src, flags=re.DOTALL)

    src = re.sub(r"(?i)\bparseDate\s*\(", "pd.to_datetime(", src)
    src = re.sub(r"(?i)\bAND\b", "&", src)
    src = re.sub(r"(?i)\bOR\b", "|", src)
    src = re.sub(r"(?i)\bNOT\b", "~", src)

    return src

def apply_calculated_fields(df: pd.DataFrame, calc_fields: List[CalculatedField]) -> pd.DataFrame:
    valid_fields = set(df.columns.tolist())
    for field in calc_fields:
        expr = field.formula.strip()
        if not expr:
            raise HTTPException(400, f"Calculated field '{field.name}' has empty formula")
        expr = _replace_field_tokens(expr)
        tokens = _token_re.findall(expr)
        for tok in sorted(set(tokens), key=lambda x: -len(x)):
            if tok in valid_fields:
                expr = re.sub(rf'(?<!df\["|df\[\')\b{re.escape(tok)}\b', f'df["{tok}"]', expr)
        expr = _translate_functions(expr, df, valid_fields)
        try:
            result = eval(expr, {"__builtins__": {}}, {"np": np, "pd": pd, "df": df})
        except Exception as e:
            try:
                result = pd.eval(expr, engine="python", local_dict={"df": df, "np": np, "pd": pd})
            except Exception as e2:
                raise HTTPException(400, f"Calculated field '{field.name}' failed: {e}; fallback pd.eval error: {e2}")
        df[field.name] = result
        valid_fields.add(field.name)
    return df

def _get_pandas_aggfunc(df: pd.DataFrame, col: str, user_agg: str):
    dtype = df[col].dtype
    agg = (user_agg or "sum").lower()
    if is_numeric_dtype(dtype):
        if agg in ("avg", "mean"): return "mean"
        if agg in ("count_distinct", "distinct", "nunique"): return pd.Series.nunique
        return agg
    else:
        if agg in ("count", "count_distinct", "distinct", "nunique"):
            if agg in ("count_distinct", "distinct", "nunique"): return pd.Series.nunique
            return "count"
        return "count"

# -----------------------------
# API endpoints
# -----------------------------
@app.get("/")
def root():
    return {"message": "Backend Running ✔"}

@app.post("/api/datasets")
def add_dataset(req: DatasetRequest):
    dataset_id = "ds_" + str(uuid.uuid4().int)[:8]
    df = load_dataset_from_source(req)
    DATASETS[dataset_id] = df
    DATASET_META[dataset_id] = {
        "id": dataset_id,
        "name": req.name,
        "source_type": req.source_type,
        "file_format": req.file_format,
        "rows": df.shape[0],
        "columns": list(df.columns)
    }
    return DATASET_META[dataset_id]

@app.get("/api/datasets")
def list_datasets():
    return list(DATASET_META.values())

@app.post("/api/activate_dataset/{dataset_id}")
def activate_dataset(dataset_id: str):
    global ACTIVE_DATASET_ID
    if dataset_id not in DATASETS:
        raise HTTPException(404, "Dataset not found")
    ACTIVE_DATASET_ID = dataset_id
    df = DATASETS[dataset_id]
    return {"dataset_id": dataset_id, "columns": list(df.columns)}

@app.get("/api/columns")
def get_columns(dataset_id: str = Query(...)):
    if dataset_id not in DATASETS:
        raise HTTPException(404, "Dataset not found")
    df = DATASETS[dataset_id]
    return {"columns": list(df.columns)}

# Global storage for per-dataset, per-column aggregation
ACTIVE_PIVOT_AGG: Dict[str, Dict[str, str]] = {}

@app.post("/api/pivot")
def generate_pivot(req: PivotRequest):
    global ACTIVE_DATASET_ID, ACTIVE_PIVOT_AGG

    if ACTIVE_DATASET_ID not in DATASETS:
        raise HTTPException(400, "No active dataset selected")

    df = DATASETS[ACTIVE_DATASET_ID].copy()

    # 1️⃣ QuickSight-style NULL & EMPTY handling
    for col in df.columns:
        df[col] = df[col].apply(
            lambda x: "__NULL__" if x is None else
                      "__EMPTY__" if isinstance(x, str) and x.strip() == "" else
                      x
        )

    # 2️⃣ Apply calculated fields
    if req.calculated_fields:
        try:
            df = apply_calculated_fields(df, req.calculated_fields)
        except Exception as e:
            raise HTTPException(400, f"Calculated field error: {e}")

    # ✅ 3️⃣ APPLY FILTERS (FIXED)
    if getattr(req, "filters", None):
        for f in req.filters:
            try:
                if f.column in df.columns:
                    df = df[df[f.column] == f.value]
            except Exception:
                continue

    # 4️⃣ Merge per-column aggregation state
    if ACTIVE_DATASET_ID not in ACTIVE_PIVOT_AGG:
        ACTIVE_PIVOT_AGG[ACTIVE_DATASET_ID] = {}

    # Update stored aggfuncs with user input
    if isinstance(req.aggfunc, dict):
        ACTIVE_PIVOT_AGG[ACTIVE_DATASET_ID].update(req.aggfunc)
    else:
        for col in req.values:
            if col not in ACTIVE_PIVOT_AGG[ACTIVE_DATASET_ID]:
                ACTIVE_PIVOT_AGG[ACTIVE_DATASET_ID][col] = req.aggfunc

    # Build agg dict for pandas pivot
    agg_dict = {}
    for col in req.values:
        user_agg = ACTIVE_PIVOT_AGG[ACTIVE_DATASET_ID].get(col, "sum")
        agg_dict[col] = _get_pandas_aggfunc(df, col, user_agg)

    # 5️⃣ Generate pivot table
    try:
        pivot = pd.pivot_table(
            df,
            index=req.rows or None,
            columns=req.columns or None,
            values=req.values,
            aggfunc=agg_dict,
            fill_value=0,
            dropna=False
        )
    except Exception as e:
        raise HTTPException(400, f"Pivot error: {e}")

    # 6️⃣ Reset index
    pivot = pivot.reset_index()

    # 7️⃣ Add QuickSight-style TOTAL row
    total_row = {}
    if req.rows:
        for col in req.rows:
            total_row[col] = "Total"

    for col in pivot.columns:
        if col not in (req.rows or []):
            try:
                total_row[col] = pivot[col].sum()
            except:
                total_row[col] = None

    pivot = pd.concat([pivot, pd.DataFrame([total_row])], ignore_index=True)

    # 8️⃣ Restore QuickSight-friendly labels
    pivot = pivot.replace({
        "__NULL__": "null",
        "__EMPTY__": "empty"
    })

    return pivot.to_dict(orient="records")


# ---------- Publish report endpoint ----------
@app.post("/api/publish-report")
def publish_report(payload: ReportPayload):
    report_id = str(uuid.uuid4())
    # Store JSON-serialized data in Redis
    r.set(f"report:{report_id}", json.dumps({
        "config": payload.report_config,
        "data": payload.report_data
    }))
    return {"report_id": report_id}

# ---------- Get report endpoint ----------
@app.get("/api/report/{report_id}")
def get_report(report_id: str):
    key = f"report:{report_id}"
    stored = r.get(key)
    if not stored:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = json.loads(stored)
    # Convert data to DataFrame for consistency
    df = pd.DataFrame(report["data"])
    return {
        "report_id": report_id,
        "config": report["config"],
        "data": df.to_dict(orient="records")
    }