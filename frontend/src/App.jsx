import { useEffect, useMemo, useState } from "react";
import GraphView from "./GraphView.jsx";
import PredictionSidebar from "./PredictionSidebar.jsx";

const API = import.meta.env.VITE_API_URL ?? "";
const REPO_URL = "https://github.com/your-username/six-degrees-of-chaos#readme";

const LOADING_LINES = [
  "Reticulating unrelated splines…",
  "Teaching GraphSAGE to gossip…",
  "Interrogating 400 Wikipedia articles…",
  "Asking the rubber duck for advice…",
  "Sampling negative edges (they were very negative)…",
  "Consulting the chaos oracle…",
];
const MIN_LOADING_MS = 1600; // long enough to read at least one joke

export default function App() {
  const [stage, setStage] = useState("landing"); // landing | loading | ready | error
  const [line, setLine] = useState(0);
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(null); // rank of the selected prediction

  useEffect(() => {
    if (stage !== "loading") return;
    const id = setInterval(() => setLine((l) => (l + 1) % LOADING_LINES.length), 700);
    return () => clearInterval(id);
  }, [stage]);

  async function summon() {
    setStage("loading");
    const started = Date.now();
    try {
      const get = async (path) => {
        const r = await fetch(`${API}${path}`);
        if (!r.ok) throw new Error(`${path} → ${r.status}`);
        return r.json();
      };
      const [graph, predictions, metrics] = await Promise.all([
        get("/api/graph"),
        get("/api/predictions"),
        get("/api/metrics").catch(() => null),
      ]);
      if (!graph.nodes?.length || !predictions?.length) throw new Error("empty data");
      await new Promise((res) => setTimeout(res, Math.max(0, MIN_LOADING_MS - (Date.now() - started))));
      setData({ graph, predictions, metrics });
      setStage("ready");
    } catch (err) {
      console.error(err);
      setStage("error");
    }
  }

  const selectedPrediction = useMemo(
    () => data?.predictions.find((p) => p.rank === selected) ?? null,
    [data, selected]
  );

  if (stage === "ready") {
    return (
      <div className="app">
        <GraphView
          graph={data.graph}
          predictions={data.predictions}
          selected={selectedPrediction}
          onSelect={setSelected}
        />
        <PredictionSidebar
          seed={data.graph.seed}
          predictions={data.predictions}
          metrics={data.metrics}
          selected={selectedPrediction}
          onSelect={setSelected}
        />
      </div>
    );
  }

  return (
    <main className="landing">
      <p className="eyebrow mono">a graph neural network experiment</p>
      <h1>
        Six Degrees of <span className="accent">Chaos</span>
      </h1>
      <p className="pitch">
        A GNN read 400 Wikipedia articles around <em>Rubber duck</em>, learned what a link looks
        like, then went looking for the ones nobody ever wrote.
      </p>

      {stage === "landing" && (
        <button className="summon" onClick={summon}>
          Summon the Chaos Graph
        </button>
      )}

      {stage === "loading" && (
        <p className="loading mono" role="status" aria-live="polite">
          <span className="spinner" aria-hidden="true" /> {LOADING_LINES[line]}
        </p>
      )}

      {stage === "error" && (
        <div className="error-card" role="alert">
          <p className="mono">The oracle is unreachable. 🦆💥</p>
          <p>
            The graph data didn't load — the backend is probably not running. Start it with{" "}
            <code>uvicorn app:app --port 8000</code> from <code>backend/</code>, or read how it all
            works in the <a href={REPO_URL}>README</a>.
          </p>
          <button className="summon ghost" onClick={summon}>
            Try again
          </button>
        </div>
      )}
    </main>
  );
}
