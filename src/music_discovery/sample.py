from __future__ import annotations

import json
import random
import sqlite3
from pathlib import Path

SEED = 20261027
TARGET = 40
# Rule fixed before listening: StreamBeats across genres, Pixabay, vocal long-tail, root singles.
QUOTAS = {"streambeats": 24, "pixabay": 6, "longtail": 6, "root": 4}
LONGTAIL_HINTS = ("church", "yoruba", "christmas", "creator", "uppbeat", "mixkit", "soundq", "nocopyright")


def bucket(row: sqlite3.Row) -> str:
    folder = (row["source_folder"] or "").lower()
    if "stream beats" in folder:
        return "streambeats"
    if folder.startswith("pixabay"):
        return "pixabay"
    if folder in ("(root)", ""):
        return "root"
    return "longtail"


def select_sample(conn: sqlite3.Connection, target: int = TARGET) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM tracks WHERE status='ok' AND duration_seconds BETWEEN 30 AND 600 ORDER BY path"
    ).fetchall()
    rng = random.Random(SEED)
    pools: dict[str, list[sqlite3.Row]] = {k: [] for k in QUOTAS}
    for row in rows:
        pools[bucket(row)].append(row)
    for pool in pools.values():
        rng.shuffle(pool)

    # Round-robin StreamBeats across genre subfolders so one genre cannot fill the quota.
    sb = pools["streambeats"]
    by_genre: dict[str, list[sqlite3.Row]] = {}
    for row in sb:
        parts = row["source_folder"].replace("/", "\\").split("\\")
        genre = "\\".join(parts[:2]) if len(parts) > 1 else row["source_folder"]
        by_genre.setdefault(genre, []).append(row)
    genres = sorted(by_genre)
    sb_ordered: list[sqlite3.Row] = []
    while len(sb_ordered) < len(sb):
        for genre in genres:
            if by_genre[genre]:
                sb_ordered.append(by_genre[genre].pop(0))
    pools["streambeats"] = sb_ordered

    picked: list[sqlite3.Row] = []
    for key, quota in QUOTAS.items():
        picked.extend(pools[key][:quota])
    if len(picked) < target:
        used = {r["id"] for r in picked}
        rest = [r for r in rows if r["id"] not in used]
        rng.shuffle(rest)
        picked.extend(rest[: target - len(picked)])
    picked = picked[:target]

    conn.execute("UPDATE tracks SET selected=0")
    out = []
    for row in picked:
        conn.execute("UPDATE tracks SET selected=1 WHERE id=?", (row["id"],))
        out.append({"id": row["id"], "path": row["path"], "source_folder": row["source_folder"],
                    "duration_seconds": row["duration_seconds"], "bucket": bucket(row)})
    conn.commit()
    return out


def write_sample(sample: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"seed": SEED, "rule": QUOTAS, "tracks": sample}, indent=2), encoding="utf-8")
