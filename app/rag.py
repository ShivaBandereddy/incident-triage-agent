# app/rag.py (Day 10: in-memory Chroma, configurable fetch/threshold, no-match fallback)
import os
import re
from pathlib import Path

_model = None
_col = None  # in-memory collection, built once per process


def _embed(texts):
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model.encode(texts).tolist()


def chunk_runbook(path):
    """One chunk per '## ' section, each prefixed with the runbook title."""
    text = Path(path).read_text()
    title = text.splitlines()[0].lstrip('# ').strip()
    parts = re.split(r'\n(?=## )', text)
    return [f'{title}\n{p.strip()}' for p in parts if len(p.strip()) > 40]


def build_index(runbook_dir='data/runbooks'):
    """Build the in-memory index (rebuilds if called again) and return the collection."""
    global _col
    import chromadb
    client = chromadb.Client()  # in-memory, nothing written to disk
    try:
        client.delete_collection('runbooks')
    except Exception:
        pass
    col = client.create_collection('runbooks')
    ids, docs, metas = [], [], []
    for p in sorted(Path(runbook_dir).glob('*.md')):
        for i, chunk in enumerate(chunk_runbook(p)):
            ids.append(f'{p.name}-{i}')
            docs.append(chunk)
            metas.append({'runbook': p.name})
    col.add(ids=ids, documents=docs, metadatas=metas, embeddings=_embed(docs))
    _col = col
    return col


def _get_collection():
    return _col if _col is not None else build_index()


def search(query, k=3, fetch=None, max_distance=None):
    """Fetch `fetch` chunks, drop chunks farther than max_distance, keep best
    chunk per runbook, return top k. Returns [] when nothing is close enough
    (the caller handles the fallback)."""
    fetch = fetch or int(os.getenv('RAG_FETCH', '8'))
    if max_distance is None:
        # starting default only: tuned on dev (Chroma default = L2 distance)
        max_distance = float(os.getenv('RAG_MAX_DISTANCE', '1.4'))
    col = _get_collection()
    res = col.query(query_embeddings=_embed([query]), n_results=fetch,
                    include=['documents', 'metadatas', 'distances'])
    best = {}
    for doc, meta, dist in zip(res['documents'][0], res['metadatas'][0], res['distances'][0]):
        if dist > max_distance:
            continue
        best.setdefault(meta['runbook'], {'runbook': meta['runbook'], 'text': doc,
                                          'distance': round(dist, 3)})
    return list(best.values())[:k]
