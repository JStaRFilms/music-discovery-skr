from __future__ import annotations

from pathlib import Path

from .embed import embed_texts, load_clap
from .queries import QUERIES
from .search import load_matrix, rank_tracks


def compare_dense(db_path: Path, model_id: str, revision: str) -> dict:
    sparse_matrix, sparse_meta = load_matrix(db_path, model_id, revision, kind="sparse")
    dense_matrix, dense_meta = load_matrix(db_path, model_id, revision, kind="dense")
    model, processor, device = load_clap(model_id, revision)
    vecs = embed_texts(model, processor, device, [q["text"] for q in QUERIES])
    per_query = []
    total_overlap = 0
    for i, query in enumerate(QUERIES):
        sparse_top = rank_tracks(sparse_matrix, sparse_meta, vecs[i], 5)
        dense_top = rank_tracks(dense_matrix, dense_meta, vecs[i], 5)
        sparse_tracks = {r["track_id"] for r in sparse_top}
        dense_tracks = {r["track_id"] for r in dense_top}
        overlap = len(sparse_tracks & dense_tracks)
        total_overlap += overlap
        per_query.append({
            "query_id": query["id"],
            "overlap_top5_tracks": overlap,
            "sparse_tracks": sorted(sparse_tracks),
            "dense_tracks": sorted(dense_tracks),
            "dense_best_scores": [round(r["score"], 4) for r in dense_top],
            "sparse_best_scores": [round(r["score"], 4) for r in sparse_top],
        })
    return {
        "sparse_windows": len(sparse_meta),
        "dense_windows": len(dense_meta),
        "mean_overlap_top5": round(total_overlap / len(QUERIES), 3) if QUERIES else 0,
        "per_query": per_query,
    }
