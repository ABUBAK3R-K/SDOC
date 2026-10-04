"""Crawl a Wikipedia link neighbourhood around one seed article.

BFS to depth 2 from SEED, capped at MAX_NODES. Depth-1 is every (non-boring)
article the seed links to; depth-2 slots are filled with the articles most
often linked from depth-1 pages, so the graph stays dense instead of stringy.

Every API response is cached in data/link_cache.json, so re-running this
script never re-fetches a page. Output: data/raw_graph.json
"""
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import requests

API = "https://en.wikipedia.org/w/api.php"
SEED = sys.argv[1] if len(sys.argv) > 1 else "Rubber duck"
MAX_NODES = 400
BATCH = 50  # MediaWiki max titles per query for anonymous clients

DATA = Path(__file__).parent / "data"
CACHE_PATH = DATA / "link_cache.json"
OUT_PATH = DATA / "raw_graph.json"

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
BORING = re.compile(
    r"^(List|Lists|Index|Outline|Glossary|Timeline) of "
    r"|\(identifier\)$|\(disambiguation\)$"
    r"|^(ISBN|ISSN|Doi|PMID|PMC|Bibcode|JSTOR|S2CID|OCLC|Wayback Machine|ArXiv|Hdl|LCCN|ASIN)\b"
    r"|^\d{1,4}s?( BC| AD| BCE| CE)?$"
    rf"|^({MONTHS}) \d{{1,2}}$"
    r"|^\d{1,2}(st|nd|rd|th) century"
    r"|^(Geographic coordinate system|Time zone|Coordinated Universal Time|UTC[+−-].*|Wikisource|Wiktionary|Wikimedia Commons|Wikidata|Wikiquote|Library of Congress)$"
)

session = requests.Session()
session.headers["User-Agent"] = "SixDegreesOfChaos/0.1 (portfolio GNN demo; codingclubclaude@gmail.com)"


def is_boring(title: str) -> bool:
    return bool(BORING.search(title))


def load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {"pages": {}, "aliases": {}}


def save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")


def canonical(cache: dict, title: str) -> str:
    return cache["aliases"].get(title, title)


def api_get(params: dict) -> dict:
    for attempt in range(5):
        try:
            r = session.get(API, params=params, timeout=30)
            if r.status_code == 429:
                raise requests.HTTPError("rate limited")
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            wait = 2 ** attempt
            print(f"  ! {e} — retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError("Wikipedia API kept failing; giving up")


def fetch(cache: dict, titles: list[str]) -> None:
    """Fetch outgoing article links + page length for titles not already cached."""
    todo = [t for t in dict.fromkeys(titles) if canonical(cache, t) not in cache["pages"]]
    for i in range(0, len(todo), BATCH):
        chunk = todo[i : i + BATCH]
        params = {
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "redirects": 1,
            "prop": "links|info",
            "plnamespace": 0,
            "pllimit": "max",
            "titles": "|".join(chunk),
        }
        pages: dict[str, dict] = {}
        while True:
            data = api_get(params)
            q = data.get("query", {})
            for m in q.get("normalized", []) + q.get("redirects", []):
                cache["aliases"][m["from"]] = m["to"]
            for p in q.get("pages", []):
                if p.get("missing") or p.get("invalid"):
                    continue
                entry = pages.setdefault(p["title"], {"links": [], "length": 0})
                entry["links"].extend(l["title"] for l in p.get("links", []))
                if "length" in p:
                    entry["length"] = p["length"]
            if "continue" not in data:
                break
            params = {**params, **data["continue"]}
        # Collapse chained aliases (normalized -> redirect -> target)
        for k, v in list(cache["aliases"].items()):
            seen = {k}
            while v in cache["aliases"] and v not in seen:
                seen.add(v)
                v = cache["aliases"][v]
            cache["aliases"][k] = v
        cache["pages"].update(pages)
        save_cache(cache)
        done = min(i + BATCH, len(todo))
        print(f"  fetched {done}/{len(todo)}")


def main() -> None:
    DATA.mkdir(exist_ok=True)
    cache = load_cache()

    print(f"Seed: {SEED}")
    fetch(cache, [SEED])
    seed = canonical(cache, SEED)
    if seed not in cache["pages"]:
        sys.exit(f"Seed article '{SEED}' not found on Wikipedia")

    # Depth 1: everything the seed links to
    depth1_raw = [t for t in cache["pages"][seed]["links"] if not is_boring(t)]
    depth1_raw = depth1_raw[: MAX_NODES - 1]
    print(f"Depth 1: {len(depth1_raw)} candidate links")
    fetch(cache, depth1_raw)

    depth = {seed: 0}
    for t in depth1_raw:
        c = canonical(cache, t)
        if c in cache["pages"] and not is_boring(c):
            depth.setdefault(c, 1)

    # Depth 2: pages shared by a *few* depth-1 pages are connective; pages shared
    # by many (United States, The New York Times...) are generic hubs that would
    # swamp the graph and make every prediction "X <-> United States".
    depth1 = [n for n, d in depth.items() if d == 1]
    counts: Counter[str] = Counter()
    for t in depth1:
        for link in set(cache["pages"][t]["links"]):
            c = canonical(cache, link)
            if c not in depth and not is_boring(c):
                counts[c] += 1
    hub_cap = max(4, len(depth1) // 10)
    eligible = {t for t, k in counts.items() if 2 <= k <= hub_cap}

    # Round-robin over depth-1 pages so every branch of the seed gets represented
    queues = []
    for t in depth1:
        own = {canonical(cache, l) for l in cache["pages"][t]["links"]} & eligible
        queues.append(sorted(own, key=lambda c: (-counts[c], c)))
    slots = MAX_NODES - len(depth)
    depth2: list[str] = []
    chosen: set[str] = set()
    while len(depth2) < slots and any(queues):
        for q in queues:
            while q and q[0] in chosen:
                q.pop(0)
            if q and len(depth2) < slots:
                chosen.add(q[0])
                depth2.append(q.pop(0))
    print(f"Depth 2: {len(depth2)} neighbours (shared by 2-{hub_cap} depth-1 pages; "
          f"{len(eligible)} eligible of {len(counts)})")
    fetch(cache, depth2)
    for t in depth2:
        c = canonical(cache, t)
        if c in cache["pages"] and not is_boring(c):
            depth.setdefault(c, 2)

    # Real edges: any link between two pages in the node set (undirected)
    edges = set()
    for u in depth:
        for link in cache["pages"][u]["links"]:
            v = canonical(cache, link)
            if v in depth and v != u:
                edges.add(tuple(sorted((u, v))))

    nodes = [
        {"title": t, "depth": d, "length": cache["pages"][t]["length"]}
        for t, d in depth.items()
    ]
    out = {"seed": seed, "nodes": nodes, "edges": sorted(edges)}
    OUT_PATH.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT_PATH.name}: {len(nodes)} nodes, {len(edges)} edges")


if __name__ == "__main__":
    main()
