from __future__ import annotations

import csv
import json
import random
import subprocess
from pathlib import Path

import numpy as np

from . import config, db as dbmod
from .embed import embed_texts, load_clap
from .search import load_matrix

TIER4_QUERIES = [
    {"id": "t4v2-sad-upbeat", "sound": "upbeat cheerful music, bright and energetic", "words": "sad heartbroken lyrics, loss and longing", "label": "sad words over an upbeat sound"},
    {"id": "t4v2-happy-sad", "sound": "sad melancholic music, slow and somber", "words": "joyful celebratory lyrics, happiness and love", "label": "happy words over a sad sound"},
    {"id": "t4v2-love-calm", "sound": "calm gentle background music, soft and sparse", "words": "romantic love lyrics, devotion and longing", "label": "love words over a calm sound"},
]


def _minmax(values: np.ndarray) -> np.ndarray:
    lo, hi = float(values.min()), float(values.max())
    if hi - lo < 1e-9:
        return np.zeros_like(values)
    return (values - lo) / (hi - lo)


def rank_lyric_query(db_path: Path, model, processor, device, sound_text: str, words_text: str, top: int = 5) -> list[dict]:
    matrix, meta = load_matrix(db_path, config.PRIMARY_MODEL_ID, config.PRIMARY_MODEL_REVISION, kind="sparse")
    conn = dbmod.connect(db_path)
    trusted = {
        r["window_id"]: r["lyric_text"]
        for r in conn.execute(
            "SELECT w.id window_id, w.lyric_text FROM windows w WHERE w.lyric_trusted=1 AND w.lyric_text IS NOT NULL AND w.lyric_text != ''"
        ).fetchall()
    }
    conn.close()
    idx = [i for i, row in enumerate(meta) if row["window_id"] in trusted]
    if not idx:
        return []
    sub = matrix[idx]
    sound_vec, words_vec = embed_texts(model, processor, device, [sound_text, words_text])
    lyric_vecs = embed_texts(model, processor, device, [trusted[meta[i]["window_id"]][:300] for i in idx])
    combined = _minmax(sub @ sound_vec) + _minmax(lyric_vecs @ words_vec)
    order = np.argsort(-combined)
    best: dict[int, dict] = {}
    for pos in order:
        row = meta[idx[int(pos)]]
        if row["track_id"] not in best:
            best[row["track_id"]] = {**row, "score": float(combined[int(pos)])}
        if len(best) >= top:
            break
    return list(best.values())


def make_tier4_pack(db_path: Path, out_dir: Path) -> dict:
    model, processor, device = load_clap(config.PRIMARY_MODEL_ID, config.PRIMARY_MODEL_REVISION)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "excerpts").mkdir(exist_ok=True)
    rng = random.Random(11)
    mapping: dict[str, dict] = {}
    rows = []
    counter = 0
    for query in TIER4_QUERIES:
        results = rank_lyric_query(db_path, model, processor, device, query["sound"], query["words"], 5)
        rng.shuffle(results)
        for res in results:
            counter += 1
            anon = f"L{counter:03d}"
            excerpt = out_dir / "excerpts" / f"{anon}.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-ss", f"{res['start_seconds']:.3f}", "-t", "10",
                 "-i", res["path"], "-ac", "1", "-ar", "48000", str(excerpt)],
                capture_output=True, timeout=120, check=False,
            )
            mapping[anon] = {"query_id": query["id"], "track_id": res["track_id"],
                             "window_start": res["start_seconds"], "path": res["path"], "score": res["score"]}
            rows.append({"query_id": query["id"], "query_text": query["label"], "tier": 4,
                         "anon_id": anon, "excerpt": f"excerpts/{anon}.wav",
                         "mark": "", "timestamp_ok": "", "failure_class": "", "notes": ""})
    with (out_dir / "judgements.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "mapping.json").write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    (out_dir / "INSTRUCTIONS.md").write_text(
        "# Tier 4 v2 — lyrics in the ranking\n\nFor each clip, judge whether BOTH halves fit: "
        "the words you hear and the sound under them. Mark usable / close / wrong in judgements.csv. "
        "Do not open mapping.json until every row is marked.\n",
        encoding="utf-8",
    )
    return {"excerpts": counter, "out_dir": str(out_dir), "queries": len(TIER4_QUERIES)}
