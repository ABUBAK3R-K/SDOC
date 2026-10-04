# Architecture: Six Degrees of Chaos

## 1. Stack
- Data collection: Python, `wikipedia-api` (or raw MediaWiki API), `networkx`
- ML: PyTorch + PyTorch Geometric (GraphSAGE encoder + dot-product decoder), scikit-learn for split utilities
- Backend: FastAPI serving precomputed JSON — no live inference per request
- Frontend: React (Vite) + react-force-graph-2d (or d3-force directly)
- Fallback scorer: `networkx` Jaccard/common-neighbors, used only if GNN training stalls

## 2. Critical design decision: precompute, don't serve live
Crawling and training per request is not viable in a 3-hour budget. The pipeline runs **once, offline**, producing `graph.json` and `predictions.json`. FastAPI just serves these static files. This is the single most important scoping decision in this project — protect it above all else.

## 3. Pipeline (offline, run once)
1. **Crawl** (`crawl.py`) — BFS from one seed article via the Wikipedia API, depth 2, capped at ~400–500 nodes. Save adjacency as `raw_graph.json` immediately (don't re-crawl on reruns).
2. **Graph build** (`build_graph.py`) — Load into `networkx.Graph`. Node features: degree, article length (proxy for importance), clustering coefficient — cheap, no embeddings needed for MVP. Convert to a PyTorch Geometric `Data` object via `torch_geometric.utils.from_networkx`.
3. **Train** (`train.py`) —
   - Split real edges train/val/test (~85/10/5) with `RandomLinkSplit`
   - Model: 2-layer GraphSAGE encoder → node embeddings → dot-product edge scores
   - Loss: binary cross-entropy with negative sampling
   - ~50–100 epochs; should run in minutes on this graph size, even on CPU
4. **Predict** (`predict.py`) — Score all non-edges, take the top 15–20 by predicted probability, filter out trivial/duplicate pairs. Attach templated captions. Save `predictions.json`.
5. **Serve** — FastAPI app with two endpoints reading the precomputed files.

## 4. API
- `GET /api/graph` → `{ nodes: [...], edges: [...] }` (real Wikipedia links)
- `GET /api/predictions` → `[{ source, target, confidence, caption, shared_neighbors }]`

## 5. File structure
```
six-degrees-of-chaos/
  backend/
    crawl.py
    build_graph.py
    train.py
    predict.py
    data/graph.json
    data/predictions.json
    app.py            # FastAPI
  frontend/
    src/App.jsx
    src/GraphView.jsx
    src/PredictionSidebar.jsx
  README.md
```

## 6. Caption generation
MVP: pick from ~6 sentence templates, fill in article titles plus the top shared neighbor. Stretch: one batched LLM call over all predictions at once (not per-edge, to save time and cost) for punchier phrasing.

## 7. Fallback ladder (use if behind schedule — see EXECUTION_PLAN.md)
1. GNN not training well by hour 2 → swap in `networkx.jaccard_coefficient` ranking, keep everything else identical. State this honestly in the README as "GNN attempted, heuristic used for time" — that honesty is itself a good interview story.
2. Frontend graph library giving trouble → fall back to a static SVG render of the top ~30 nodes instead of a full interactive force graph.
3. Live Wikipedia crawl slow/rate-limited → use a small pre-bundled Wikipedia sample dataset instead.
