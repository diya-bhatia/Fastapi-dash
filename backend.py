from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, date
from decimal import Decimal
import io, re, json, html as htmllib, boto3, polars as pl, os

# =====================================================
# FastAPI setup
# =====================================================
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# Global state
# =====================================================
DATASETS: Dict[str, pl.DataFrame] = {}
DATASET_META: Dict[str, Dict] = {}  # stores name, source_type, file_format
ACTIVE_DATASET_ID: Optional[str] = None

# =====================================================
# Utility functions
# =====================================================
def json_serial(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def is_numeric_dtype(dtype: pl.DataType) -> bool:
    try:
        return pl.datatypes.is_numeric(dtype)
    except Exception:
        return dtype in {pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                         pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
                         pl.Float32, pl.Float64} or str(dtype).startswith("Decimal")

def build_expr(formula: str, columns: List[str]) -> pl.Expr:
    expr = htmllib.unescape(formula)
    parts = re.split(r'(".*?"|\'.*?\')', expr)

    def replace_cols(segment: str) -> str:
        for c in columns:
            segment = re.sub(
                rf'(?<![A-Za-z0-9_]){re.escape(c)}(?![A-Za-z0-9_])',
                f'pl.col("{c}")', segment
            )
        return segment

    for i in range(0, len(parts), 2):
        parts[i] = replace_cols(parts[i])

    expr = "".join(parts)
    allowed_globals = {"pl": pl, "abs": abs, "round": round}

    try:
        return eval(expr, {"__builtins__": {}}, allowed_globals)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid formula '{formula}': {e}")

def cast_filter_values_for_col(dtype: pl.DataType, values: List[str]):
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

def apply_filters_and_calcs(df: pl.DataFrame, filters: Dict[str, List[str]], calculated_fields: Dict[str, str]) -> pl.DataFrame:
    # Apply filters
    for col, vals in (filters or {}).items():
        if col not in df.columns:
            continue
        col_dtype = df.schema[col]
        casted_vals = cast_filter_values_for_col(col_dtype, vals or [])
        df = df.filter(pl.col(col).is_in(casted_vals))
    # Calculated fields
    for new_col, formula in (calculated_fields or {}).items():
        if not formula or not isinstance(formula, str):
            raise HTTPException(status_code=400, detail=f"Formula for '{new_col}' must be a non-empty string")
        expr = build_expr(formula, df.columns)
        df = df.with_columns(expr.alias(new_col))
    return df

# =====================================================
# Models
# =====================================================
class DatasetRequest(BaseModel):
    name: str
    source_type: str = "s3"  # "s3" or "local"
    file_format: str = "parquet"  # "parquet" or "csv"
    s3: Optional[Dict[str, str]] = None
    local_path: Optional[str] = None

class PivotRequest(BaseModel):
    rows: Optional[List[str]] = []
    columns: Optional[List[str]] = []
    values: Optional[List[str]] = []
    filters: Optional[Dict[str, List[str]]] = {}
    calculated_fields: Optional[Dict[str, str]] = {}
    aggfunc: str = "sum"

class DistinctRequest(BaseModel):
    column: str
    filters: Optional[Dict[str, List[str]]] = {}
    calculated_fields: Optional[Dict[str, str]] = {}

# =====================================================
# Routes
# =====================================================
@app.get("/")
def health():
    return {"status": "FastAPI backend is running ✅"}

@app.get("/api/datasets")
def list_datasets():
    return [
        {
            "id": ds_id,
            "name": DATASET_META.get(ds_id, {}).get("name", ds_id),
            "source_type": DATASET_META.get(ds_id, {}).get("source_type", "unknown"),
            "file_format": DATASET_META.get(ds_id, {}).get("file_format", "unknown"),
            "rows": df.shape[0],
            "cols": df.shape[1],
            "columns": list(df.columns)
        }
        for ds_id, df in DATASETS.items()
    ]

@app.post("/api/datasets")
async def add_dataset(request: DatasetRequest):
    global ACTIVE_DATASET_ID
    try:
        if request.source_type == "s3":
            if not request.s3 or "bucket" not in request.s3 or "key" not in request.s3:
                raise HTTPException(status_code=400, detail="Missing S3 bucket/key")
            s3 = boto3.client("s3")
            obj = s3.get_object(Bucket=request.s3["bucket"], Key=request.s3["key"])
            buffer = io.BytesIO(obj["Body"].read())
            if request.file_format == "parquet":
                df = pl.read_parquet(buffer)
            elif request.file_format == "csv":
                df = pl.read_csv(buffer)
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format")
        elif request.source_type == "local":
            if not request.local_path or not os.path.exists(request.local_path):
                raise HTTPException(status_code=400, detail=f"File not found: {request.local_path}")
            if request.file_format == "parquet":
                df = pl.read_parquet(request.local_path)
            elif request.file_format == "csv":
                df = pl.read_csv(request.local_path)
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format")
        else:
            raise HTTPException(status_code=400, detail="Unsupported source_type")

        ds_id = f"ds_{int(datetime.now().timestamp())}"
        DATASETS[ds_id] = df
        DATASET_META[ds_id] = {
            "name": request.name,
            "source_type": request.source_type,
            "file_format": request.file_format
        }
        ACTIVE_DATASET_ID = ds_id

        return {"id": ds_id, "name": request.name, "columns": list(df.columns), "status": "Dataset added successfully ✅"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {e}")

@app.post("/api/activate_dataset/{dataset_id}")
def activate_dataset(dataset_id: str):
    global ACTIVE_DATASET_ID
    if dataset_id not in DATASETS:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    ACTIVE_DATASET_ID = dataset_id
    return {"active_dataset": dataset_id}

# ✅ FIXED ENDPOINT (works with Dash frontend)
@app.get("/api/columns")
def get_columns(dataset_id: Optional[str] = None):
    """
    Return list of columns for the requested dataset,
    or for the active one if none is specified.
    """
    global ACTIVE_DATASET_ID
    ds_id = dataset_id or ACTIVE_DATASET_ID
    if not ds_id or ds_id not in DATASETS:
        raise HTTPException(status_code=404, detail="No active dataset found")

    df = DATASETS[ds_id]
    # You can return just names or name+type for better frontend info
    columns = [{"name": col, "dtype": str(df.schema[col])} for col in df.columns]
    return {"columns": columns}

@app.post("/api/pivot")
def pivot_data(req: PivotRequest):
    if not ACTIVE_DATASET_ID or ACTIVE_DATASET_ID not in DATASETS:
        raise HTTPException(status_code=500, detail="No active dataset selected")
    df = DATASETS[ACTIVE_DATASET_ID].clone()
    df = apply_filters_and_calcs(df, req.filters or {}, req.calculated_fields or {})

    agg_cols = req.values or []
    if not agg_cols:
        raise HTTPException(status_code=400, detail="No value columns provided")
    missing = [c for c in agg_cols if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Value columns not found: {missing}")

    if req.aggfunc.lower() in {"sum", "mean"}:
        for col in agg_cols:
            dtype = df.schema[col]
            if not is_numeric_dtype(dtype):
                df = df.with_columns(pl.col(col).cast(pl.Float64).alias(col))

    group_cols = [c for c in (req.rows or []) + (req.columns or []) if c in df.columns]

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

    result = df.group_by(group_cols).agg(agg_exprs) if group_cols else df.select(agg_exprs)
    json_bytes = json.dumps(result.to_dicts(), default=json_serial).encode("utf-8")
    return StreamingResponse(io.BytesIO(json_bytes), media_type="application/json")

@app.post("/api/distinct")
def distinct_values(req: DistinctRequest):
    if not ACTIVE_DATASET_ID or ACTIVE_DATASET_ID not in DATASETS:
        raise HTTPException(status_code=500, detail="No active dataset selected")
    df = DATASETS[ACTIVE_DATASET_ID].clone()
    df = apply_filters_and_calcs(df, req.filters or {}, req.calculated_fields or {})

    if req.column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{req.column}' not found")

    vals = df.select(pl.col(req.column)).unique().to_series().to_list()
    vals_json = json.loads(json.dumps(vals, default=json_serial))
    return {"column": req.column, "values": vals_json}
