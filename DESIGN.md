# Design: Six Degrees of Chaos — UX & Visual Spec

## 1. Vibe
Not a corporate dashboard — a mischievous science experiment. Dark background, one glowing accent color, playful copy throughout ("the chaos oracle," "reticulating unrelated splines").

## 2. Screens

### 2.1 Landing / Loading
- Centered title + one-line pitch + single button: "Summon the Chaos Graph"
- On click: loading state cycling through playful status lines while data loads

### 2.2 Graph View (main screen)
- Full-bleed force-directed graph (react-force-graph-2d or raw d3-force)
- Real Wikipedia links: thin solid gray edges
- Predicted "chaos" links: dashed, glowing accent-color edges, subtle pulse animation
- Nodes: circle sized by degree, article title shown on hover/zoom
- Sidebar (collapsible on mobile): top predictions ranked by confidence; clicking one focuses that edge in the graph

### 2.3 Prediction detail (on click/hover of a predicted edge)
- Small card: "{Article A} ↔ {Article B}" with confidence % and a one-line generated caption
- Optional "why?" toggle: shows 2–3 shared-neighbor articles that drove the prediction

## 3. Visual language
- Palette: near-black background (#0d0d0f), off-white text, one saturated accent (electric purple or teal) reserved for predicted edges
- Typography: monospace for data/labels (reinforces the "graph" feel), clean sans-serif for body copy
- Motion: subtle only — pulsing predicted edges, smooth pan/zoom. No heavy transitions; this is a time-boxed build.

## 4. Copy tone
Dry, nerdy-funny, never mean. Example caption: "{A} and {B} have never met. The graph is convinced they'd get along."

## 5. Empty / error states
If the crawl or model output fails to load, show a static message pointing to the GitHub repo/README instead of a blank screen — never a silent failure.

## 6. Mobile
Graph view is pinch-zoomable and scrollable; sidebar collapses into a bottom sheet.
