from __future__ import annotations

import csv
import json
import random
import sqlite3
import subprocess
from pathlib import Path

from .queries import QUERIES


def make_blind_pack(db_path: Path, results_by_query: dict[str, list[dict]], out_dir: Path) -> dict:
    """Write anonymised excerpt wavs + judgements.csv. Mapping stays in a separate file."""
    out_dir.mkdir(parents=True, exist_ok=True)
    excerpt_dir = out_dir / "excerpts"
    excerpt_dir.mkdir(exist_ok=True)
    rng = random.Random(7)
    mapping: dict[str, dict] = {}
    rows: list[dict] = []
    counter = 0
    for query in QUERIES:
        results = list(results_by_query.get(query["id"], []))
        rng.shuffle(results)
        for rank, res in enumerate(results, start=1):
            counter += 1
            anon = f"R{counter:03d}"
            excerpt = excerpt_dir / f"{anon}.wav"
            cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{res['start_seconds']:.3f}",
                   "-t", "10", "-i", res["path"], "-ac", "1", "-ar", "48000", str(excerpt)]
            subprocess.run(cmd, capture_output=True, timeout=120, check=False)
            mapping[anon] = {"query_id": query["id"], "track_id": res["track_id"],
                             "window_start": res["start_seconds"], "path": res["path"], "score": res["score"]}
            rows.append({"query_id": query["id"], "query_text": query["text"], "tier": query["tier"],
                         "anon_id": anon, "excerpt": f"excerpts/{anon}.wav",
                         "mark": "", "timestamp_ok": "", "failure_class": "", "notes": ""})
    with (out_dir / "judgements.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["query_id"])
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "mapping.json").write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    (out_dir / "INSTRUCTIONS.md").write_text(
        "# Blind judging\n\nListen to each excerpt without opening mapping.json. "
        "Mark each row in judgements.csv: usable / close / wrong, timestamp_ok yes/no, "
        "failure_class if wrong. Reveal filenames only after every row is marked.\n",
        encoding="utf-8")
    return {"excerpts": counter, "out_dir": str(out_dir)}


def scorecard(db_path: Path, judgements_csv: Path) -> dict:
    marks: dict[str, list[str]] = {}
    total = usable = 0
    with judgements_csv.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if not row.get("mark"):
                continue
            total += 1
            marks.setdefault(row["query_id"], []).append(row["mark"].strip().lower())
            if row["mark"].strip().lower() == "usable":
                usable += 1
    by_query = {q: {"n": len(v), "usable": v.count("usable"),
                    "precision_at_5": round(v.count("usable") / len(v), 3) if v else 0}
                for q, v in marks.items()}
    return {"judged": total, "usable": usable,
            "overall_precision": round(usable / total, 3) if total else 0, "by_query": by_query}


def seed_judgements_table(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("SELECT 1 FROM judgements LIMIT 1").fetchone()
    conn.close()
