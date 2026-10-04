# PRD: Six Degrees of Chaos

## 1. One-liner
A GNN-powered Wikipedia link predictor that finds absurd-but-plausible "missing links" between articles that have never been connected — then explains why the graph thinks they should be.

## 2. Problem / Motivation
Recommendation systems (your target specialization) are really just "link prediction in disguise." This project turns that into something visibly fun and shareable instead of another sterile MovieLens demo — while still being a legitimate GNN project you can defend in an interview.

## 3. Goals
- Ship a working, demo-able full-stack app in a 3-hour build window
- Demonstrate real GNN link-prediction skills (not a toy sklearn model)
- Produce at least 10 genuinely funny/interesting predicted connections
- Learn: PyTorch Geometric basics, link-prediction task framing, graph data pipelines end to end

## 4. Non-goals
- Production-scale Wikipedia crawling
- Real-time per-request training or crawling
- User accounts, auth, or persistence beyond one demo dataset
- Perfect natural-language captions (templated is acceptable for v1)

## 5. Users
- Recruiters/portfolio reviewers: click a link, poke around, are entertained/impressed within 60 seconds
- You: hands-on repetition of the GNN pipeline you're specializing in

## 6. Core user story
"As a visitor, I open the demo, see a graph of real Wikipedia links radiating from one seed article, and can click a glowing dashed 'predicted' edge to see the GNN's confidence score plus a witty one-line explanation of the imagined connection."

## 7. Features (MVP, priority order)
1. Precomputed graph (~300–500 nodes) from one seed article, with real edges pulled from Wikipedia
2. GraphSAGE-style GNN trained for link prediction on held-out real edges
3. Top 15–20 "chaos" predictions: highest-scoring non-edges
4. Templated snark caption per predicted edge
5. FastAPI serving the precomputed graph + predictions as JSON
6. Interactive force-directed graph frontend: real edges (solid, gray) vs. predicted (dashed, glowing), click for caption + confidence
7. One-page README explaining the ML approach in plain language, for interview storytelling

## 8. Stretch goals (only if time remains)
- Dropdown to switch between 2–3 precomputed seed graphs
- Single batched LLM call to punch up captions instead of templates
- Public deploy (Render/Vercel) instead of local-only demo

## 9. Success criteria
- App runs end-to-end locally within the 3-hour window
- At least 10 predicted edges are legible and funny, not noise
- README clearly explains what the GNN actually learned, in your own words

## 10. Risks
- PyTorch Geometric install friction → fall back to a Jaccard/common-neighbors score that ships on time; note this honestly in the README
- Wikipedia API rate limits mid-crawl → cache crawl output to disk immediately after crawling, don't re-fetch on every run
