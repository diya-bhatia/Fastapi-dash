# pivot.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, date
from decimal import Decimal

import io
import re
import json
import html as htmllib  # unescape &gt; &lt; etc.
import boto3
import polars as pl

# ===== FastAPI app =====
app = FastAPI()

# ===== Enable CORS (FastAPI style) =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # TODO: in prod, restrict to your Dash domain/port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== S3 dataset config =====
BUCKET_NAME = "prod-datalake-adhoc"
OBJECT_KEY = "adhoc_datapipeline/silver/overdue_report/part-00000-6d22d859-e324-4915-9429-f5478f1155bb-c000.snappy.parquet"

# ===== Load dataset from S3 at startup =====
try:
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY)
    buffer = io.BytesIO(obj["Body"].read())
    df2 = pl.read_parquet(buffer)
    print(f"[pivot] Loaded dataset: rows={df2.shape[0]} cols={df2.shape[1]}")
except Exception as e:
    print("[pivot] Error loading S3 data:", e)
    df2 = pl.DataFrame()  # empty fallback

# ===== Helpers =====
def json_serial(obj):
    """Custom JSON serializer for Decimal and datetime/date."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def is_numeric_dtype(dtype: pl.DataType) -> bool:
    """Check numerics; Decimal can be represented differently, so string match too."""
    try:
        return pl.datatypes.is_numeric(dtype)  # type: ignore
    except Exception:
        return (
            dtype in {
                pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
                pl.Float32, pl.Float64,
            }
            or str(dtype).startswith("Decimal")
        )

def build_expr(formula: str, columns: List[str]) -> pl.Expr:
    """
    Hardened formula builder:
      - Unescape HTML entities (&gt; -> >, &lt; -> <)
      - Replace bare column names with pl.col("...") only outside quotes
      - Evaluate using a restricted globals dict
    Supports both styles:
      - bare columns: price * quantity
      - explicit: pl.col("price") * pl.col("quantity")
    """
    # 1) Unescape HTML entities
    expr = htmllib.unescape(formula)

    # 2) Replace column tokens outside quotes
    parts = re.split(r'(".*?"|\'.*?\')', expr)

    def replace_cols(segment: str) -> str:
        for c in columns:
            # Replace exact identifiers (not substrings)
            segment = re.sub(
                rf'(?<![A-Za-z0-9_]){re.escape(c)}(?![A-Za-z0-9_])',
                f'pl.col("{c}")',
                segment
            )
        return segment

    for i in range(0, len(parts), 2):  # only non-quoted segments
        parts[i] = replace_cols(parts[i])

    expr = "".join(parts)

    # 3) Safe eval
    allowed_globals = {"pl": pl, "abs": abs, "round": round}
    try:
        return eval(expr, {"__builtins__": {}}, allowed_globals)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid formula '{formula}': {e}")

def cast_filter_values_for_col(dtype: pl.DataType, values: List[str]):
    """Cast filter values to the target column dtype so is_in works correctly."""
    casted = []
    for v in values:
        try:
            if dtype in {pl.Utf8, pl.String}:
                casted.append(str(v))
            elif is_numeric_dtype(dtype):
                casted.append(float(v))
            elif dtype in {pl.Boolean}:
                casted.append(str(v).strip().lower() in {"true", "1", "yes"})
            elif dtype in {pl.Date}:
                casted.append(datetime.fromisoformat(v).date())
            elif dtype in {pl.Datetime}:
                casted.append(datetime.fromisoformat(v))
            else:
                casted.append(v)
        except Exception:
            casted.append(v)
    return casted

# ===== API models =====
class PivotRequest(BaseModel):
    rows: Optional[List[str]] = []
    columns: Optional[List[str]] = []
    values: Optional[List[str]] = []
    filters: Optional[Dict[str, List[str]]] = {}
    calculated_fields: Optional[Dict[str, str]] = {}
    aggfunc: str = "sum"  # 'sum' | 'mean' | 'count' | 'max' | 'min'

class DistinctRequest(BaseModel):
    column: str
    filters: Optional[Dict[str, List[str]]] = {}
    calculated_fields: Optional[Dict[str, str]] = {}

# ===== Routes =====
@app.get("/")
def health():
    return {"status": "FastAPI backend is running ✅"}

@app.get("/columns")
def get_columns():
    """Return column names for the loaded dataframe."""
    return df2.columns if not df2.is_empty() else []

def apply_filters_and_calcs(df: pl.DataFrame, filters: Dict[str, List[str]], calculated_fields: Dict[str, str]) -> pl.DataFrame:
    # Filters first
    for col, vals in (filters or {}).items():
        if col not in df.columns:
            continue
        col_dtype = df.schema[col]
        casted_vals = cast_filter_values_for_col(col_dtype, vals or [])
        df = df.filter(pl.col(col).is_in(casted_vals))

    # Calculated fields (order matters)
    for new_col, formula in (calculated_fields or {}).items():
        if not formula or not isinstance(formula, str):
            raise HTTPException(status_code=400, detail=f"Formula for '{new_col}' must be a non-empty string")
        expr = build_expr(formula, df.columns)
        try:
            df = df.with_columns(expr.alias(new_col))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error computing '{new_col}': {e}")

    return df

@app.post("/api/pivot")
def pivot_data(req: PivotRequest):
    if df2.is_empty():
        raise HTTPException(status_code=500, detail="No data loaded from S3")

    df = df2.clone()
    df = apply_filters_and_calcs(df, req.filters or {}, req.calculated_fields or {})

    agg_cols = req.values or []
    if not agg_cols:
        raise HTTPException(status_code=400, detail="No value columns provided")

    # Ensure all value columns exist after calcs
    missing = [c for c in agg_cols if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Value columns not found: {missing}")

    # For sum/mean, enforce numeric casting
    if req.aggfunc.lower() in {"sum", "mean"}:
        for col in agg_cols:
            dtype = df.schema[col]
            if not is_numeric_dtype(dtype):
                try:
                    df = df.with_columns(pl.col(col).cast(pl.Float64).alias(col))
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Column '{col}' is not numeric and cannot be cast to Float64: {e}"
                    )

    # Grouping
    group_cols = [c for c in (req.rows or []) + (req.columns or []) if c in df.columns]

    # Aggregations
    agg_exprs = []
    agg = req.aggfunc.lower()
    for col in agg_cols:
        if agg == "sum":
            agg_exprs.append(pl.col(col).sum().alias(f"{col}_sum"))
        elif agg == "mean":
            agg_exprs.append(pl.col(col).mean().alias(f"{col}_mean"))
        elif agg == "count":
            agg_exprs.append(pl.len().alias(f"{col}_count"))
        elif agg == "max":
            agg_exprs.append(pl.col(col).max().alias(f"{col}_max"))
        elif agg == "min":
            agg_exprs.append(pl.col(col).min().alias(f"{col}_min"))
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported aggregation: {req.aggfunc}")

    try:
        result = df.group_by(group_cols).agg(agg_exprs) if group_cols else df.select(agg_exprs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Aggregation error: {e}")

    records = result.to_dicts()
    json_bytes = json.dumps(records, default=json_serial).encode("utf-8")
    return StreamingResponse(io.BytesIO(json_bytes), media_type="application/json")

@app.post("/api/distinct")
def distinct_values(req: DistinctRequest):
    """Return distinct values for a column (after applying filters + calculated fields)."""
    if df2.is_empty():
        raise HTTPException(status_code=500, detail="No data loaded from S3")

    if not req.column:
        raise HTTPException(status_code=400, detail="Column name required")

    df = df2.clone()
    df = apply_filters_and_calcs(df, req.filters or {}, req.calculated_fields or {})

    if req.column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{req.column}' not found after applying calculated fields")

    try:
        vals = df.select(pl.col(req.column)).unique().to_series().to_list()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute distinct values: {e}")

    vals_json = json.loads(json.dumps(vals, default=json_serial))
    return {"column": req.column, "values": vals_json}