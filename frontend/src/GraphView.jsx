import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import PredictionCard from "./PredictionCard.jsx";

export const ACCENT = "#b46cff";
// Muted community colours so the accent stays reserved for predictions
const PALETTE = ["#5f7fa8", "#6f9a82", "#a8906a", "#8f78a6", "#5f9c9a", "#a67480", "#8a8f6a"];

const idOf = (end) => (typeof end === "object" ? end.id : end);
const edgeKey = (a, b) => (a < b ? `${a}|${b}` : `${b}|${a}`);

// Screen-px offset that moves a focused edge out from under the prediction card
// (card sits top-left on desktop, full-width top on mobile — see styles.css)
export const cardShift = (width) => (width > 760 ? { x: 210, y: 0 } : { x: 0, y: 130 });

export default function GraphView({ graph, predictions, selected, onSelect }) {
  const fgRef = useRef();
  const wrapRef = useRef();
  const fitted = useRef(false);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [hoverNode, setHoverNode] = useState(null);

  useEffect(() => {
    const ro = new ResizeObserver(([e]) =>
      setSize({ w: e.contentRect.width, h: e.contentRect.height })
    );
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  const data = useMemo(
    () => ({
      nodes: graph.nodes.map((n) => ({ ...n })),
      links: [
        ...graph.edges.map((e) => ({ source: e.source, target: e.target, predicted: false })),
        ...predictions.map((p) => ({ source: p.source, target: p.target, predicted: true, rank: p.rank })),
      ],
    }),
    [graph, predictions]
  );

  const predictedEnds = useMemo(
    () => new Set(predictions.flatMap((p) => [p.source, p.target])),
    [predictions]
  );

  // What lights up when a prediction is selected: its ends + the "why" articles
  const focus = useMemo(() => {
    if (!selected) return null;
    const why = selected.path.length ? selected.path : [selected.source, ...selected.shared_neighbors, selected.target];
    const nodes = new Set([selected.source, selected.target, ...why]);
    const edges = new Set();
    if (selected.path.length) {
      for (let i = 0; i < why.length - 1; i++) edges.add(edgeKey(why[i], why[i + 1]));
    } else {
      for (const s of selected.shared_neighbors) {
        edges.add(edgeKey(selected.source, s));
        edges.add(edgeKey(selected.target, s));
      }
    }
    return { nodes, edges };
  }, [selected]);

  // Predicted links must not pull nodes together — they aren't real (yet)
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    fg.d3Force("charge").strength(-45);
    fg.d3Force("link")
      .distance(35)
      .strength((l) => (l.predicted ? 0 : 0.7 / Math.min(l.source.degree || 1, l.target.degree || 1)));
    fg.d3ReheatSimulation();
  }, [data]);

  // Fly to the selected prediction, framing it in the area the card doesn't cover
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg || !selected) return;
    const byId = (id) => data.nodes.find((n) => n.id === id);
    const a = byId(selected.source);
    const b = byId(selected.target);
    if (!a || a.x == null || !b) return;
    const shift = cardShift(size.w);
    const freeW = size.w - 2 * shift.x;
    const freeH = size.h - 2 * shift.y - 80; // legend / bottom sheet
    const zoom = Math.min(
      5,
      (freeW * 0.6) / (Math.abs(a.x - b.x) || 1),
      (freeH * 0.6) / (Math.abs(a.y - b.y) || 1)
    );
    fg.centerAt((a.x + b.x) / 2 - shift.x / zoom, (a.y + b.y) / 2 - shift.y / zoom, 700);
    fg.zoom(zoom, 700);
  }, [selected, data, size.w, size.h]);

  const drawNode = (node, ctx, scale) => {
    const r = 1.6 + Math.sqrt(node.degree) * 0.45;
    const lit = focus?.nodes.has(node.id);
    const isEnd = selected && (node.id === selected.source || node.id === selected.target);
    ctx.globalAlpha = focus && !lit ? 0.18 : 1;

    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = PALETTE[node.group % PALETTE.length];
    ctx.fill();
    if (predictedEnds.has(node.id)) {
      ctx.lineWidth = (isEnd ? 2.5 : 1.2) / scale;
      ctx.strokeStyle = ACCENT;
      ctx.stroke();
    }

    const showLabel = lit || node === hoverNode || node.depth === 0 || scale > 2.6;
    if (showLabel) {
      const fontSize = (isEnd ? 13 : 11) / scale;
      ctx.font = `${isEnd ? 600 : 400} ${fontSize}px "JetBrains Mono", monospace`;
      const w = ctx.measureText(node.id).width;
      const y = node.y + r + fontSize * 0.9;
      ctx.fillStyle = "rgba(13,13,15,0.75)";
      ctx.fillRect(node.x - w / 2 - 2 / scale, y - fontSize * 0.75, w + 4 / scale, fontSize * 1.1);
      ctx.fillStyle = isEnd ? "#f4ecff" : "#d6d6dc";
      ctx.textAlign = "center";
      ctx.fillText(node.id, node.x, y);
    }
    ctx.globalAlpha = 1;
  };

  const drawPredicted = (link, ctx, scale) => {
    const { source: s, target: t } = link;
    if (s.x == null || t.x == null) return;
    const now = performance.now() / 1000;
    const active = selected?.rank === link.rank;
    ctx.save();
    ctx.globalAlpha = selected && !active ? 0.2 : 0.65 + 0.35 * Math.sin(now * 2.5 + link.rank);
    ctx.strokeStyle = ACCENT;
    ctx.lineWidth = (active ? 3.2 : 1.8) / scale;
    ctx.setLineDash([7 / scale, 5 / scale]);
    ctx.lineDashOffset = (-now * 24) / scale;
    ctx.shadowColor = ACCENT;
    ctx.shadowBlur = active ? 20 : 10;
    ctx.beginPath();
    ctx.moveTo(s.x, s.y);
    ctx.lineTo(t.x, t.y);
    ctx.stroke();
    ctx.restore();
  };

  // Only predicted links are clickable; real ones are scenery
  const paintPointer = (link, color, ctx, scale) => {
    if (!link.predicted) return;
    ctx.strokeStyle = color;
    ctx.lineWidth = 10 / scale;
    ctx.beginPath();
    ctx.moveTo(link.source.x, link.source.y);
    ctx.lineTo(link.target.x, link.target.y);
    ctx.stroke();
  };

  const realLinkColor = (link) => {
    if (focus?.edges.has(edgeKey(idOf(link.source), idOf(link.target)))) return "rgba(220,200,255,0.85)";
    return focus ? "rgba(150,150,165,0.03)" : "rgba(150,150,165,0.075)";
  };

  return (
    <section className="graph-wrap" ref={wrapRef} aria-label="Wikipedia link graph">
      {size.w > 0 && (
        <ForceGraph2D
          ref={fgRef}
          width={size.w}
          height={size.h}
          graphData={data}
          backgroundColor="#0d0d0f"
          nodeId="id"
          nodeLabel={(n) => `${n.id} · ${n.degree} links`}
          nodeCanvasObject={drawNode}
          nodePointerAreaPaint={(node, color, ctx) => {
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(node.x, node.y, 3 + Math.sqrt(node.degree) * 0.45, 0, 2 * Math.PI);
            ctx.fill();
          }}
          linkColor={realLinkColor}
          linkWidth={(l) => (focus?.edges.has(edgeKey(idOf(l.source), idOf(l.target))) ? 1.6 : 0.5)}
          linkCanvasObjectMode={(l) => (l.predicted ? "replace" : undefined)}
          linkCanvasObject={drawPredicted}
          linkPointerAreaPaint={paintPointer}
          onLinkClick={(l) => l.predicted && onSelect(l.rank)}
          onNodeHover={setHoverNode}
          onNodeClick={(n) => {
            const p = predictions.find((p) => p.source === n.id || p.target === n.id);
            if (p) onSelect(p.rank);
          }}
          onBackgroundClick={() => onSelect(null)}
          autoPauseRedraw={false}
          warmupTicks={80}
          cooldownTicks={200}
          onEngineStop={() => {
            if (!fitted.current) {
              fitted.current = true;
              fgRef.current?.zoomToFit(600, 40);
            }
          }}
        />
      )}

      <div className="legend mono" aria-hidden="true">
        <span><i className="swatch real" /> real Wikipedia link</span>
        <span><i className="swatch predicted" /> GNN-predicted chaos link</span>
        <span className="hint">click a glowing edge · scroll to zoom</span>
      </div>

      {selected && <PredictionCard prediction={selected} onClose={() => onSelect(null)} />}
    </section>
  );
}
