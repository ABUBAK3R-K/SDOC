"""raw_graph.json -> networkx graph -> PyTorch Geometric Data object.

Node features are cheap structural signals, no text embeddings:
  log degree, log article length, clustering coefficient, PageRank, BFS depth (one-hot)
Outputs:
  data/graph.pt    — PyG Data (x, edge_index, titles) for training
  data/graph.json  — nodes (with Louvain community) / edges for the frontend
"""
import json
import math
from pathlib import Path

import networkx as nx
import torch
from torch_geometric.utils import from_networkx

DATA = Path(__file__).parent / "data"


def main() -> None:
    raw = json.loads((DATA / "raw_graph.json").read_text(encoding="utf-8"))

    G = nx.Graph()
    for n in raw["nodes"]:
        G.add_node(n["title"], depth=n["depth"], length=n["length"])
    G.add_edges_from(raw["edges"])

    clustering = nx.clustering(G)
    communities = nx.community.louvain_communities(G, seed=42)
    group = {t: i for i, c in enumerate(sorted(communities, key=len, reverse=True)) for t in c}
    pagerank = nx.pagerank(G)
    feats = {}
    for t in G.nodes:
        d = G.nodes[t]["depth"]
        feats[t] = [
            math.log1p(G.degree[t]),
            math.log1p(G.nodes[t]["length"]),
            clustering[t],
            math.log(pagerank[t] * len(G)),
            float(d == 0), float(d == 1), float(d == 2),
        ]

    # Standardise each feature column (skip the one-hot depth columns)
    x = torch.tensor([feats[t] for t in G.nodes], dtype=torch.float)
    mu, sd = x[:, :4].mean(0), x[:, :4].std(0).clamp_min(1e-6)
    x[:, :4] = (x[:, :4] - mu) / sd

    # Convert a bare integer-labelled copy, then attach features + titles
    titles = list(G.nodes)
    index = {t: i for i, t in enumerate(titles)}
    bare = nx.Graph()
    bare.add_nodes_from(range(len(titles)))
    bare.add_edges_from((index[u], index[v]) for u, v in G.edges)
    data = from_networkx(bare)
    data.x = x
    data.titles = titles
    assert data.x.shape == (G.number_of_nodes(), 7)
    assert data.edge_index.max().item() < data.num_nodes
    torch.save(data, DATA / "graph.pt")
    print(data)

    # Frontend payload
    nodes = [
        {
            "id": t,
            "depth": G.nodes[t]["depth"],
            "degree": G.degree[t],
            "group": group[t],
            "url": "https://en.wikipedia.org/wiki/" + t.replace(" ", "_"),
        }
        for t in G.nodes
    ]
    edges = [{"source": u, "target": v} for u, v in G.edges]
    (DATA / "graph.json").write_text(
        json.dumps({"seed": raw["seed"], "nodes": nodes, "edges": edges}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"graph.json: {len(nodes)} nodes, {len(edges)} edges, {len(communities)} communities")


if __name__ == "__main__":
    main()
