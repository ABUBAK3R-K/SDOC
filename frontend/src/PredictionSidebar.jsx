import { useState } from "react";

export default function PredictionSidebar({ seed, predictions, metrics, selected, onSelect }) {
  const [open, setOpen] = useState(false); // bottom-sheet state on mobile only

  return (
    <aside className={`sidebar ${open ? "open" : ""}`}>
      <button className="sheet-handle mono" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        {open ? "▾ hide" : "▴"} {predictions.length} chaos predictions
      </button>

      <header>
        <h1>
          Six Degrees of <span className="accent">Chaos</span>
        </h1>
        <p className="mono sub">
          seed: {seed} · GraphSAGE link prediction
          {metrics && (
            <>
              <br />
              test AUC {metrics.test_auc.toFixed(2)} (Jaccard baseline {metrics.jaccard_test_auc.toFixed(2)})
            </>
          )}
        </p>
      </header>

      <ol className="predictions">
        {predictions.map((p) => (
          <li key={p.rank}>
            <button
              className={selected?.rank === p.rank ? "active" : ""}
              onClick={() => {
                onSelect(selected?.rank === p.rank ? null : p.rank);
                setOpen(false);
              }}
            >
              <span className="mono pct">{Math.floor(p.confidence * 100)}%</span>
              <span className="pair">
                {p.source} <span className="accent">↔</span> {p.target}
              </span>
            </button>
          </li>
        ))}
      </ol>
    </aside>
  );
}
