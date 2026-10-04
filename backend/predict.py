"""Score every non-edge with the trained GNN and keep the best "chaos" links.

A pair makes the cut if it is:
  - not already linked on Wikipedia (we only score non-edges)
  - cross-community (Louvain): same-cluster predictions are obvious, not chaos
  - low neighbour overlap (Jaccard): if they already share half their friends,
    a heuristic would predict it too — chaos is where the GNN sees what Jaccard can't
  - not hub <-> hub (Germany <-> Reuters is true but boring)
  - not a title echo (Bering Strait <-> Bering Sea)
  - not reusing an article, or over-using one pair of communities (keeps it varied)
Each survivor gets a "why": its shared neighbours, or, when it has none,
the shortest real path between the two articles. Then a templated caption.
Output: data/predictions.json
"""
import json
import re
import sys
from pathlib import Path

import networkx as nx
import torch

from train import LinkPredictor

DATA = Path(__file__).parent / "data"
TOP_K = 20
HUB_DEGREE = 50
MAX_JACCARD = 0.12
MAX_USES_PER_NODE = 1
MAX_PER_COMMUNITY_PAIR = 2

STOPWORDS = {"the", "of", "and", "a", "an", "in", "on", "for", "to", "de", "la", "company", "song"}

TEMPLATES = [
    "{a} and {b} have never met. The graph is convinced they'd get along — they're both very into {c}.",
    "Nobody on Wikipedia has introduced {a} to {b}. {c} has been dropping hints for years.",
    "If {a} and {b} were at a party, they'd end up in the kitchen talking about {c}.",
    "The oracle formally proposes a crossover episode: {a} × {b}, brought to you by {c}.",
    "{a} has never linked to {b}. {c}, who knows them both, finds this deeply awkward.",
    "Somewhere in latent space, {a} and {b} are already holding hands. {c} was the wingman.",
    "{a} and {b}: separated at birth, reunited by gradient descent. Paternity test: {c}.",
    "Peer review pending: {a} and {b} have {n} mutual {friends}, including {c}. Suspicious.",
    "Editors missed it, the GNN didn't: {a} belongs next to {b}. Exhibit A: {c}.",
    "{a} walks into a bar. {b} is already there, deep in conversation with {c}.",
]
# For pairs with no shared neighbour: {path} is the shortest real link chain
PATH_TEMPLATES = [
    "{a} and {b} have zero mutual friends. The GNN found a back alley anyway: {path}.",
    "Officially strangers. Unofficially: {path}. The graph is never wrong (citation needed).",
    "Six degrees? Try {k}. {path}. The oracle has spoken.",
    "No one introduced {a} to {b}. Gradient descent did, via {path}.",
]


def display(title: str) -> str:
    """'Convoy (song)' -> 'Convoy' for captions; full title stays the id."""
    return re.sub(r"\s*\([^)]*\)$", "", title)


def words(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", display(title).lower()) if w not in STOPWORDS and len(w) > 2}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles choke on "→"
    data = torch.load(DATA / "graph.pt", weights_only=False)
    graph = json.loads((DATA / "graph.json").read_text(encoding="utf-8"))
    ckpt = torch.load(DATA / "model.pt", weights_only=False)
    titles = data.titles
    n = data.num_nodes
    meta = {node["id"]: node for node in graph["nodes"]}

    model = LinkPredictor(ckpt["in_dim"])
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    with torch.no_grad():
        z = model.encode(data.x, data.edge_index)  # full real graph at inference
        prob = (z @ z.t()).sigmoid()

    adj = torch.zeros(n, n, dtype=torch.bool)
    adj[data.edge_index[0], data.edge_index[1]] = True
    candidates = torch.triu(torch.ones(n, n, dtype=torch.bool), diagonal=1) & ~adj
    scores = prob.masked_fill(~candidates, -1.0).flatten()
    order = scores.argsort(descending=True)
    print(f"Scored {int(candidates.sum())} non-edges")

    G = nx.Graph()
    G.add_nodes_from(titles)
    G.add_edges_from((titles[u], titles[v]) for u, v in data.edge_index.t().tolist())

    degree = adj.sum(1)
    uses = [0] * n
    pair_uses: dict[tuple[int, int], int] = {}
    picked = []
    for flat in order.tolist():
        if len(picked) == TOP_K or scores[flat] < 0:
            break
        i, j = divmod(flat, n)
        a, b = titles[i], titles[j]
        groups = tuple(sorted((meta[a]["group"], meta[b]["group"])))
        if groups[0] == groups[1] or pair_uses.get(groups, 0) >= MAX_PER_COMMUNITY_PAIR:
            continue
        if degree[i] > HUB_DEGREE and degree[j] > HUB_DEGREE:
            continue
        if words(a) & words(b) or display(a) in b or display(b) in a:
            continue
        if uses[i] >= MAX_USES_PER_NODE or uses[j] >= MAX_USES_PER_NODE:
            continue
        shared = (adj[i] & adj[j]).nonzero().flatten().tolist()
        union = (adj[i] | adj[j]).sum().item()
        if union and len(shared) / union > MAX_JACCARD:
            continue
        uses[i] += 1
        uses[j] += 1
        pair_uses[groups] = pair_uses.get(groups, 0) + 1

        # "Why": shared neighbours, most specific (lowest-degree) first
        shared.sort(key=lambda k: (degree[k].item(), titles[k]))
        shared_titles = [titles[k] for k in shared]
        path = [] if shared_titles else nx.shortest_path(G, a, b)

        rank = len(picked)
        if shared_titles:
            caption = TEMPLATES[rank % len(TEMPLATES)].format(
                a=display(a), b=display(b), c=display(shared_titles[0]),
                n=len(shared_titles), friends="friend" if len(shared_titles) == 1 else "friends",
            )
        else:
            caption = PATH_TEMPLATES[rank % len(PATH_TEMPLATES)].format(
                a=display(a), b=display(b), k=len(path) - 1,
                path=" → ".join(display(t) for t in path),
            )
        caption = re.sub(r"([.?!])\.(?!\.)", lambda m: m.group(1), caption)  # "D.C.." -> "D.C."

        picked.append({
            "rank": rank + 1,
            "source": a,
            "target": b,
            "confidence": round(scores[flat].item(), 4),
            "caption": caption,
            "shared_neighbors": shared_titles[:3],
            "shared_count": len(shared_titles),
            "path": path,
        })

    (DATA / "predictions.json").write_text(
        json.dumps(picked, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    for p in picked:
        print(f"{p['confidence']:.3f}  {p['source']} <-> {p['target']}  [{p['shared_count']} shared, path {len(p['path'])}]")
        print(f"        {p['caption']}")
    print(f"\nWrote predictions.json ({len(picked)} predictions)")


if __name__ == "__main__":
    main()
