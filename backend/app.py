"""FastAPI server for the precomputed graph + predictions. No live inference.

    uvicorn app:app --reload --port 8000

If frontend/dist exists (npm run build), it is served at / as well.
"""
import json
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

DATA = Path(__file__).parent / "data"
DIST = Path(__file__).parent.parent / "frontend" / "dist"

app = FastAPI(title="Six Degrees of Chaos")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


@lru_cache
def load(name: str):
    path = DATA / name
    if not path.exists():
        raise HTTPException(503, f"{name} not built yet — run the pipeline (see README)")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/graph")
def graph():
    return load("graph.json")


@app.get("/api/predictions")
def predictions():
    return load("predictions.json")


@app.get("/api/metrics")
def metrics():
    return load("metrics.json")


if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
