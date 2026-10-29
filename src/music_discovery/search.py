from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np


def load_matrix(db_path: Path, model_id: str, revision: str, kind: str | None = "sparse"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    kind_sql = " AND w.kind=?" if kind else ""
    params = (model_id, revision, kind) if kind else (model_id, revision)
    rows = conn.execute(
        f"""SELECT e.row_index, e.window_id, w.track_id, w.start_seconds, w.end_seconds, t.path, t.rel_path
           FROM embeddings e JOIN windows w ON w.id=e.window_id JOIN tracks t ON t.id=w.track_id
           WHERE e.model_id=? AND e.model_revision=?{kind_sql} ORDER BY e.row_index""",
        params,
    ).fetchall()
    conn.close()
    emb_path = db_path.parent / f"embeddings-{model_id.replace('/', '_')}.npy"
    matrix = np.load(emb_path)
    meta = [dict(r) for r in rows if r["row_index"] < len(matrix)]
    return matrix[[r["row_index"] for r in meta]], meta


def duplicate_groups(matrix: np.ndarray, meta: list[dict], threshold: float = 0.995) -> dict[int, int]:
    """Map each track to the canonical id of its near-duplicate group.

    A track's fingerprint is the mean of its sparse window embeddings.
    Measured on the real library, identical recordings in different
    folders score 0.998+, while merely similar songs from one album stay
    under 0.995 — hence the conservative threshold. Tracks with no twin
    map to themselves.
    """
    order: list[int] = []
    sums: dict[int, np.ndarray] = {}
    counts: dict[int, int] = {}
    for i, row in enumerate(meta):
        tid = row["track_id"]
        if tid not in sums:
            sums[tid] = np.zeros(matrix.shape[1], dtype=np.float64)
            counts[tid] = 0
            order.append(tid)
        sums[tid] += matrix[i]
        counts[tid] += 1
    if not order:
        return {}
    means = np.array([sums[t] / counts[t] for t in order])
    means /= np.maximum(np.linalg.norm(means, axis=1, keepdims=True), 1e-12)
    sims = means @ means.T
    parent = {t: t for t in order}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a in range(len(order)):
        for b in range(a + 1, len(order)):
            if sims[a, b] >= threshold:
                ra, rb = find(order[a]), find(order[b])
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)
    return {t: find(t) for t in order}


def rank_tracks(matrix: np.ndarray, meta: list[dict], query_vec: np.ndarray, top_tracks: int = 5,
                adjustments: np.ndarray | None = None, groups: dict[int, int] | None = None) -> list[dict]:
    scores = matrix @ query_vec
    if adjustments is not None:
        scores = scores + adjustments
    order = np.argsort(-scores)
    best: dict[int, dict] = {}
    for idx in order:
        row = meta[int(idx)]
        tid = row["track_id"]
        key = groups.get(tid, tid) if groups else tid
        if key not in best:
            entry = {**row, "score": float(scores[int(idx)])}
            if adjustments is not None:
                entry["personal_adjustment"] = float(adjustments[int(idx)])
            best[key] = entry
        if len(best) >= top_tracks:
            break
    return list(best.values())
