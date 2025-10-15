from datetime import datetime, date
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import polars as pl
import json
import uuid
import os
import boto3
import io
from decimal import Decimal  # ✅ Add this

app = FastAPI()

s3 = boto3.client("s3")

BUCKET_NAME = "prod-datalake-adhoc"

# chart
# OBJECT_KEY_1 = "adhoc_datapipeline/silver/overdue_dpd_count/part-00000-ee01c7fa-3005-4610-934f-cbd335c3bf9e-c000.snappy.parquet"
# obj1 = s3.get_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY_1)
# buffer1 = io.BytesIO(obj1["Body"].read())
# df1 = pl.read_parquet(buffer1)

# table
OBJECT_KEY_2 = "adhoc_datapipeline/silver/overdue_report/part-00000-bfe21fea-c9ed-431c-b00a-c82bfdf72be7-c000.snappy.parquet"
obj2 = s3.get_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY_2)
buffer2 = io.BytesIO(obj2["Body"].read())
df2 = pl.read_parquet(buffer2)

# ✅ Custom encoder for Decimal values
def json_serial(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()  # Convert to string "YYYY-MM-DD"
    raise TypeError(f"Type {type(obj)} not serializable")


@app.get("/")
def stream_data():
    def generate():
        for row in df2.iter_rows(named=True):
            yield json.dumps(row, default=json_serial) + "\n"  # ✅ Fix here
    return StreamingResponse(generate(), media_type="application/json")

    
@app.get("/columns")
def get_columns():
    return df2.columns


