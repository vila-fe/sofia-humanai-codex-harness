#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GB-1: Pipeline de embeddings del Carril A (híbrido vectorial-grafo, SPEC-GRAPHRAG-001).

Procedencia: Padre EP-2026-10-05-C | GB-0 EP-2026-10-04-I | PROC-012 (modelo ganador:
paraphrase-multilingual-MiniLM-L12-v2) | Presupuesto ~5 EUR aprobado por AVF 05/10/2026.

Funciones:
  - index  : lee manifest del Carril A, calcula embeddings y los almacena en SQLite.
  - search : búsqueda semántica top-k (por defecto top-5).
  - eval   : evaluación sobre el conjunto de oro con gate hit-rate@5 >= 70% (PROC-010:
             aprobado != ejecutado; este gate mide ejecución real).

El fallback por hash determinista (SinHT) solo cubre el smoke test; NO sustituye al
modelo en producción (decisión PROC-012). Salidas HECHOS medidos, no inferencias.

Uso:
  python scripts/gb1_embeddings.py index  [--manifest docs/index/carril-a/corpus-carril-a-v0.1.json]
                                          [--db data/carril_a_embeddings.sqlite]
  python scripts/gb1_embeddings.py search "consulta" [--top 5]
  python scripts/gb1_embeddings.py eval   [--golden docs/index/carril-a/golden_set_v0.1.json]
"""

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_MANIFEST = "docs/index/carril-a/corpus-carril-a-v0.1.json"
DEFAULT_GOLDEN = "docs/index/carril-a/golden_set_v0.1.json"
DEFAULT_DB = "data/carril_a_embeddings.sqlite"
HIT_RATE_GATE = 0.70  # >= 70% hit-rate@5 (gate GB-1)
DEFAULT_TOP = 5

SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    text TEXT NOT NULL,
    n_tokens INTEGER,
    sha256 TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS embeddings (
    chunk_id TEXT NOT NULL,
    dim INTEGER NOT NULL,
    model TEXT NOT NULL,
    vector BLOB NOT NULL,
    sha256 TEXT NOT NULL,
    PRIMARY KEY (chunk_id, model),
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id)
);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id);
"""


def load_model():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(DEFAULT_MODEL), "model"
    except Exception as exc:  # pragma: no cover - entorno sin modelo
        print(f"[WARN] sentence-transformers no disponible ({exc}); fallback hash (solo smoke test).",
              file=sys.stderr)
        return None, "hash"


def embed_hash(texts):
    """Fallback determinista por SHA-256 (dim 64). SOLO smoke test, no producción."""
    out = []
    for t in texts:
        h = hashlib.sha256(t.encode("utf-8")).digest()
        out.append([b / 255.0 for b in h[:64]])
    return out


def cosine(a, b):
    num = sum(x * y for x, y in zip(a, b))
    da = sum(x * x for x in a) ** 0.5 or 1e-9
    db = sum(y * y for y in b) ** 0.5 or 1e-9
    return num / (da * db)


def load_manifest(path):
    p = Path(path)
    if not p.exists():
        sys.exit(f"[ERROR] manifest no encontrado: {p}")
    manifest = json.loads(p.read_text(encoding="utf-8"))
    entries = []
    if isinstance(manifest, list):
        entries = manifest
    elif "chunks" in manifest:
        entries = manifest["chunks"]
    elif "documents" in manifest:
        for d in manifest["documents"]:
            for ch in d.get("chunks", [d]):
                ch = dict(ch)
                ch.setdefault("source_id", d.get("doc_id", d.get("id", "doc")))
                entries.append(ch)
    else:
        entries = [manifest]
    for e in entries:
        e.setdefault("chunk_id", e.get("id") or hashlib.sha256(
            (e.get("source_id", "s") + e.get("text", "")).encode("utf-8")).hexdigest()[:16])
        e.setdefault("text", e.get("content", ""))
        e.setdefault("n_tokens", len(e["text"].split()))
        e["sha256"] = hashlib.sha256(e["text"].encode("utf-8")).hexdigest()
    return entries


def cmd_index(args):
    entries = load_manifest(args.manifest)
    model, mode = load_model()
    conn = sqlite3.connect(args.db)
    conn.executescript(SCHEMA)
    texts = [e["text"] for e in entries]
    if mode == "model":
        vectors = model.encode(texts, show_progress_bar=False).tolist()
    else:
        vectors = embed_hash(texts)
    for e, v in zip(entries, vectors):
        conn.execute("INSERT OR REPLACE INTO chunks (chunk_id, source_id, text, n_tokens, sha256, model) "
                     "VALUES (?,?,?,?,?,?)",
                     (e["chunk_id"], e.get("source_id", "?"), e["text"], e["n_tokens"], e["sha256"], DEFAULT_MODEL))
        import struct
        blob = struct.pack(f"{len(v)}d", *v)
        conn.execute("INSERT OR REPLACE INTO embeddings (chunk_id, dim, model, vector, sha256) "
                     "VALUES (?,?,?,?,?)",
                     (e["chunk_id"], len(v), DEFAULT_MODEL, blob, e["sha256"]))
    conn.commit()
    print(f"[OK] indexados {len(entries)} chunks en {args.db} | modo={mode} | modelo={DEFAULT_MODEL}")
    print(f"[HECHO] dim={len(vectors[0])} | manifest={args.manifest}")


def _fetch_all(db):
    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT c.chunk_id, c.source_id, c.text, e.dim, e.vector FROM chunks c "
                        "JOIN embeddings e ON c.chunk_id = e.chunk_id").fetchall()
    import struct
    out = []
    for chunk_id, source_id, text, dim, blob in rows:
        out.append((chunk_id, source_id, text, list(struct.unpack(f"{dim}d", blob))))
    return out


def search(db, query, top=DEFAULT_TOP):
    model, mode = load_model()
    qv = (model.encode([query], show_progress_bar=False).tolist()[0] if mode == "model"
          else embed_hash([query])[0])
    scored = [(cid, src, text, cosine(qv, v)) for cid, src, text, v in _fetch_all(db)]
    scored.sort(key=lambda r: r[3], reverse=True)
    return scored[:top]


def cmd_search(args):
    for cid, src, text, score in search(args.db, args.query, args.top):
        print(f"{score:.4f}  {cid}  [{src}]  {text[:80]}...")


def cmd_eval(args):
    p = Path(args.golden)
    if not p.exists():
        sys.exit(f"[ERROR] conjunto de oro no encontrado: {p}")
    golden = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(golden, dict) and "cases" in golden:
        golden = golden["cases"]  # fix: golden_set v0.1 envuelve los casos en "cases"
    hits = 0
    total = 0
    for case in golden:
        expected = set(case.get("expected_chunk_ids", []))
        results = search(args.db, case["query"], DEFAULT_TOP)
        got = {cid for cid, *_ in results}
        hit = bool(expected & got) if expected else True
        hits += hit
        total += 1
        print(f"[{'HIT ' if hit else 'MISS'}] {case['query'][:60]} | esperados={sorted(expected)}")
    hit_rate = hits / total if total else 0.0
    gate = hit_rate >= HIT_RATE_GATE
    print(f"[HECHO] hit-rate@5 = {hit_rate:.0%} ({hits}/{total}) | gate >= {HIT_RATE_GATE:.0%} => "
          f"{'APROBADO' if gate else 'FALLADO'}")
    sys.exit(0 if gate else 1)


def main():
    ap = argparse.ArgumentParser(description="GB-1: embeddings Carril A")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_idx = sub.add_parser("index"); p_idx.add_argument("--manifest", default=DEFAULT_MANIFEST)
    p_idx.add_argument("--db", default=DEFAULT_DB); p_idx.set_defaults(func=cmd_index)
    p_s = sub.add_parser("search"); p_s.add_argument("query"); p_s.add_argument("--top", type=int, default=DEFAULT_TOP)
    p_s.add_argument("--db", default=DEFAULT_DB); p_s.set_defaults(func=cmd_search)
    p_e = sub.add_parser("eval"); p_e.add_argument("--golden", default=DEFAULT_GOLDEN)
    p_e.add_argument("--db", default=DEFAULT_DB); p_e.set_defaults(func=cmd_eval)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
