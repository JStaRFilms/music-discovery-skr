from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np


def load_matrix(db_path: Path, model_id: str, revision: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT e.row_index, e.window_id, w.track_id, w.start_seconds, w.end_seconds, t.path, t.rel_path
           FROM embeddings e JOIN windows w ON w.id=e.window_id JOIN tracks t ON t.id=w.track_id
           WHERE e.model_id=? AND e.model_revision=? ORDER BY e.row_index""",
        (model_id, revision),
    ).fetchall()
    conn.close()
    emb_path = db_path.parent / f"embeddings-{model_id.replace('/', '_')}.npy"
    matrix = np.load(emb_path)
    meta = [dict(r) for r in rows if r["row_index"] < len(matrix)]
    return matrix[[r["row_index"] for r in meta]], meta


def rank_tracks(matrix: np.ndarray, meta: list[dict], query_vec: np.ndarray, top_tracks: int = 5) -> list[dict]:
    scores = matrix @ query_vec
    order = np.argsort(-scores)
    best: dict[int, dict] = {}
    for idx in order:
        row = meta[int(idx)]
        tid = row["track_id"]
        if tid not in best:
            best[tid] = {**row, "score": float(scores[int(idx)])}
        if len(best) >= top_tracks:
            break
    return list(best.values())
