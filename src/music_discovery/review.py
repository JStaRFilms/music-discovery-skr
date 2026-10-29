from __future__ import annotations

import csv
import html
import subprocess
from pathlib import Path

from . import config, db as dbmod


def _fmt(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def make_lyrics_review(db_path: Path, out_dir: Path) -> dict:
    conn = dbmod.connect(db_path)
    rows = conn.execute(
        """SELECT w.id window_id, w.start_seconds, w.end_seconds, w.vocal_prob, w.lyric_confidence,
                  w.lyric_text, t.rel_path, t.path
           FROM windows w JOIN tracks t ON t.id=w.track_id
           WHERE w.lyric_text IS NOT NULL AND w.lyric_text != ''
           ORDER BY w.vocal_prob DESC"""
    ).fetchall()
    conn.close()

    excerpt_dir = out_dir / "excerpts"
    excerpt_dir.mkdir(parents=True, exist_ok=True)
    csv_rows = []
    cards = []
    for row in rows:
        name = f"W{row['window_id']}.wav"
        out = excerpt_dir / name
        if not out.exists():
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-ss", f"{row['start_seconds']:.3f}", "-t", "10",
                 "-i", row["path"], "-ac", "1", "-ar", "16000", str(out)],
                capture_output=True, timeout=120, check=False,
            )
        csv_rows.append({
            "window_id": row["window_id"],
            "track": row["rel_path"],
            "passage": f"{_fmt(row['start_seconds'])}-{_fmt(row['end_seconds'])}",
            "confidence": row["lyric_confidence"],
            "lyric_text": row["lyric_text"],
            "excerpt": f"excerpts/{name}",
            "words_match": "",
            "notes": "",
        })
        cards.append(
            f"""<article class="card">
  <div class="meta"><strong>{html.escape(Path(row['rel_path']).name)}</strong>
  <span>{html.escape(row['rel_path'])}</span>
  <span>passage {_fmt(row['start_seconds'])}–{_fmt(row['end_seconds'])}</span>
  <span>vocal {row['vocal_prob']:.2f} · confidence {row['lyric_confidence']}</span></div>
  <audio controls preload="none" src="excerpts/{name}"></audio>
  <p class="words">{html.escape(row['lyric_text'] or '')}</p>
</article>"""
        )

    with (out_dir / "review.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(csv_rows[0].keys()) if csv_rows else ["window_id"])
        writer.writeheader()
        writer.writerows(csv_rows)

    (out_dir / "index.html").write_text(
        """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Lyrics review — do the words match?</title>
<style>
body{background:#16130f;color:#f2ede6;font-family:"Segoe UI",system-ui,sans-serif;margin:0}
main{width:min(860px,100% - 40px);margin:0 auto;padding:36px 0 60px}
h1{font-size:26px} p.lede{color:#b9b0a2}
.card{background:#211c16;border:1px solid #3a332a;border-radius:10px;padding:16px;margin:12px 0}
.meta{display:flex;gap:14px;flex-wrap:wrap;color:#b9b0a2;font-size:13px;margin-bottom:10px}
.meta strong{color:#f2ede6;font-size:15px}
audio{width:100%;max-width:520px;height:36px}
.words{font-size:16px;line-height:1.5;margin:12px 0 2px}
</style></head><body><main>
<h1>Do the words match what you hear?</h1>
<p class="lede">Play each 10-second passage and compare it with the transcribed words under it.
Mark each row in review.csv: right, partly, or wrong. Low confidence rows are the ones to watch.</p>
"""
        + "\n".join(cards)
        + "</main></body></html>",
        encoding="utf-8",
    )
    return {"passages": len(rows), "out_dir": str(out_dir)}
