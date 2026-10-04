import { useState } from "react";

const wiki = (t) => `https://en.wikipedia.org/wiki/${encodeURIComponent(t.replace(/ /g, "_"))}`;

export default function PredictionCard({ prediction: p, onClose }) {
  const [why, setWhy] = useState(false);

  return (
    <article className="card" aria-live="polite">
      <button className="close" onClick={onClose} aria-label="Close">×</button>
      <p className="mono rank">chaos link #{p.rank}</p>
      <h2>
        <a href={wiki(p.source)} target="_blank" rel="noreferrer">{p.source}</a>
        <span className="accent"> ↔ </span>
        <a href={wiki(p.target)} target="_blank" rel="noreferrer">{p.target}</a>
      </h2>
      <div className="confidence mono">
        <span>{(p.confidence * 100).toFixed(1)}% confident</span>
        <span className="bar"><span style={{ width: `${p.confidence * 100}%` }} /></span>
      </div>
      <p className="caption">{p.caption}</p>

      <button className="why mono" onClick={() => setWhy((w) => !w)} aria-expanded={why}>
        {why ? "▾" : "▸"} why?
      </button>
      {why && (
        <div className="why-body">
          {p.shared_count > 0 ? (
            <>
              <p>
                They share {p.shared_count} neighbour{p.shared_count === 1 ? "" : "s"} on the real
                graph. The most specific:
              </p>
              <ul className="mono">
                {p.shared_neighbors.map((n) => (
                  <li key={n}><a href={wiki(n)} target="_blank" rel="noreferrer">{n}</a></li>
                ))}
              </ul>
            </>
          ) : (
            <>
              <p>No shared neighbours at all. Shortest real path the GNN could have smelled:</p>
              <ol className="mono path">
                {p.path.map((n) => (
                  <li key={n}><a href={wiki(n)} target="_blank" rel="noreferrer">{n}</a></li>
                ))}
              </ol>
            </>
          )}
          <p className="fine">
            The score itself comes from GraphSAGE embeddings, which blend each article's own
            features with its neighbours' — these are the clues, not the full reasoning.
          </p>
        </div>
      )}
    </article>
  );
}
