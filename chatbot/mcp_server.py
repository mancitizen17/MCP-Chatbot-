# mcp_server.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
from uuid import uuid4
import pandas as pd, json, re
from io import BytesIO

app = FastAPI(title="Model-Context-Protocol (MCP) Server")

# Allow calls from Streamlit (localhost:8501)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#######################################################################
#  In-memory “collections”  (id → {"filename", "type", "data"})
#######################################################################
collections: Dict[str, Dict[str, Any]] = {}


@app.get("/collections")
def list_collections():
    """Return minimal metadata so the UI can build its dropdown."""
    return {
        "collections": [
            {
                "id": cid,
                "metadata": {
                    "filename": meta["filename"],
                    "type": meta["type"],
                },
            }
            for cid, meta in collections.items()
        ]
    }


@app.post("/upload/")
async def upload(file: UploadFile = File(...)):
    """Accept json/xlsx/csv/txt and store its content in RAM."""
    raw = await file.read()
    name = file.filename.lower()

    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(BytesIO(raw))
        data, ftype = df.to_dict(orient="records"), "excel"
    elif name.endswith(".csv"):
        df = pd.read_csv(BytesIO(raw))
        data, ftype = df.to_dict(orient="records"), "csv"
    elif name.endswith(".json"):
        data, ftype = json.loads(raw.decode()), "json"
    elif name.endswith(".txt"):
        data, ftype = raw.decode(), "txt"
    else:
        raise HTTPException(400, "Unsupported file type")

    cid = str(uuid4())
    collections[cid] = {"filename": file.filename, "type": ftype, "data": data}
    return {"id": cid, "status": "stored"}


class Query(BaseModel):
    collection_id: str
    query: str


@app.post("/query/")
def query_collection(body: Query):
    """Very naive full-text search over the chosen collection."""
    coll = collections.get(body.collection_id)
    if not coll:
        raise HTTPException(404, "Collection not found")

    q = body.query.lower()
    hits: List[Any] = []

    if coll["type"] in ("txt",):
        hits = [line for line in coll["data"].splitlines() if q in line.lower()]

    elif coll["type"] in ("json", "csv", "excel"):
        for row in coll["data"]:
            if q in json.dumps(row).lower():
                hits.append(row)

    return {"results": hits[:5]}  # limit to top 5
