# Execution Plan — 3 Hour Build

Hand this file (plus PRD.md, DESIGN.md, ARCHITECTURE.md) to Claude Code directly. Each block is time-boxed with a hard checkpoint. If a block runs over, jump straight to the fallback ladder in ARCHITECTURE.md §7 rather than debugging further — protect the finish line, not any one component.

## Hour 1 — Data (0:00–1:00)
- **0:00–0:15** — Scaffold repo (`backend/`, `frontend/`), install deps: `torch`, `torch_geometric`, `networkx`, `fastapi`, `uvicorn`, `wikipedia-api`
- **0:15–0:40** — Write & run `crawl.py`: BFS from one whimsical seed article (e.g. "Napoleon" or "Rubber duck"), depth 2, cap 400 nodes → `raw_graph.json`
  - ✅ Checkpoint: `raw_graph.json` has 300+ nodes, edges look sane
- **0:40–1:00** — Write `build_graph.py`: load into networkx, compute node features, export a PyG `Data` object, pickle it
  - ✅ Checkpoint: PyG object loads without shape errors

## Hour 2 — Model (1:00–2:00)
- **1:00–1:25** — Write `train.py`: `RandomLinkSplit`, 2-layer GraphSAGE, training loop, print val AUC every 10 epochs
  - ✅ Checkpoint: val AUC > 0.7. If much lower by epoch 50, don't over-tune — move on
- **1:25–1:45** — Write `predict.py`: score all non-edges, take top 15–20, dedupe/filter trivial pairs
  - ✅ Checkpoint: `predictions.json` has 15+ interesting-looking pairs (spot-check a few titles)
- **1:45–2:00** — Write caption templates, attach to predictions, save final `predictions.json`
  - ✅ Checkpoint: captions read naturally, no leftover template artifacts

## Hour 3 — App + Polish (2:00–3:00)
- **2:00–2:15** — FastAPI `app.py`: two GET endpoints serving the JSON files, CORS enabled
- **2:15–2:45** — React frontend: force-directed graph component, real-vs-predicted edge styling, click-to-reveal caption card
  - ✅ Checkpoint: graph renders, at least one predicted edge is clickable and shows a caption
- **2:45–2:55** — Polish pass: loading-state copy, empty-state fallback, quick responsive check
- **2:55–3:00** — Write `README.md`: what it does, how the GNN works in 3 sentences, screenshot placeholder, "built in 3 hours" note

## If you're behind at any checkpoint
Cut in this order:
1. Drop caption polish → keep templates plain
2. Drop the hover "why" shared-neighbors feature
3. Fall back to Jaccard scoring instead of the GNN
4. Fall back to a static SVG instead of the interactive graph

Never cut: the real-vs-predicted edge distinction. That contrast is the entire point of the demo.
