"""Train a 2-layer GraphSAGE link predictor on the Wikipedia graph.

Encoder: SAGEConv -> ReLU -> SAGEConv gives each article a 64-d embedding.
Decoder: dot product of two embeddings = logit that a link exists.
Real edges are split 85/10/5 (train/val/test); each epoch samples fresh
random non-edges as negatives and minimises binary cross-entropy.
Saves data/model.pt (weights + metrics).
"""
import json
from pathlib import Path

import networkx as nx
import torch
import torch.nn.functional as F
from sklearn.metrics import roc_auc_score
from torch_geometric import seed_everything
from torch_geometric.nn import SAGEConv
from torch_geometric.transforms import RandomLinkSplit
from torch_geometric.utils import negative_sampling

DATA = Path(__file__).parent / "data"
EPOCHS = 400
SEED = 7


class LinkPredictor(torch.nn.Module):
    def __init__(self, in_dim: int, hidden: int = 128, out: int = 64):
        super().__init__()
        self.conv1 = SAGEConv(in_dim, hidden)
        self.conv2 = SAGEConv(hidden, out)

    def encode(self, x, edge_index):
        h = F.relu(self.conv1(x, edge_index))
        h = F.dropout(h, p=0.3, training=self.training)
        return self.conv2(h, edge_index)

    @staticmethod
    def decode(z, pairs):
        return (z[pairs[0]] * z[pairs[1]]).sum(-1)


@torch.no_grad()
def evaluate(model, split) -> float:
    model.eval()
    z = model.encode(split.x, split.edge_index)
    scores = model.decode(z, split.edge_label_index).sigmoid()
    return roc_auc_score(split.edge_label.numpy(), scores.numpy())


def jaccard_auc(train, split) -> float:
    """Heuristic baseline: Jaccard coefficient on the training graph only."""
    G = nx.Graph()
    G.add_nodes_from(range(train.num_nodes))
    G.add_edges_from(train.edge_index.t().tolist())
    pairs = split.edge_label_index.t().tolist()
    scores = [s for _, _, s in nx.jaccard_coefficient(G, pairs)]
    return roc_auc_score(split.edge_label.numpy(), scores)


def main() -> None:
    seed_everything(SEED)  # PyG negative sampling uses python `random`, not just torch
    data = torch.load(DATA / "graph.pt", weights_only=False)
    titles = data.titles
    del data.titles

    split = RandomLinkSplit(
        num_val=0.10, num_test=0.05, is_undirected=True,
        add_negative_train_samples=False,
    )
    train, val, test = split(data)

    model = LinkPredictor(data.num_features)
    opt = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)

    best_val, best_state = 0.0, None
    for epoch in range(1, EPOCHS + 1):
        model.train()
        opt.zero_grad()
        z = model.encode(train.x, train.edge_index)
        pos = train.edge_label_index
        neg = negative_sampling(train.edge_index, num_nodes=train.num_nodes,
                                num_neg_samples=pos.size(1))
        logits = torch.cat([model.decode(z, pos), model.decode(z, neg)])
        labels = torch.cat([torch.ones(pos.size(1)), torch.zeros(neg.size(1))])
        loss = F.binary_cross_entropy_with_logits(logits, labels)
        loss.backward()
        opt.step()

        val_auc = evaluate(model, val)
        if val_auc > best_val:
            best_val = val_auc
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        if epoch % 10 == 0:
            print(f"epoch {epoch:3d}  loss {loss.item():.4f}  val AUC {val_auc:.4f}")

    model.load_state_dict(best_state)
    test_auc = evaluate(model, test)
    baseline = jaccard_auc(train, test)
    print(f"\nbest val AUC {best_val:.4f} | test AUC {test_auc:.4f} | Jaccard baseline test AUC {baseline:.4f}")

    metrics = {"val_auc": round(best_val, 4), "test_auc": round(test_auc, 4),
               "jaccard_test_auc": round(baseline, 4), "epochs": EPOCHS}
    torch.save({"state_dict": best_state, "in_dim": data.num_features, "metrics": metrics},
               DATA / "model.pt")
    (DATA / "metrics.json").write_text(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
