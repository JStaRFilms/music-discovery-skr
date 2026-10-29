from __future__ import annotations

import json
import math
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import numpy as np

from . import config, db as dbmod
from .embed import embed_texts, load_clap
from .search import load_matrix

VOCAL_PROMPT = "a song with a singing voice and vocals"
INSTRUMENTAL_PROMPT = "instrumental music with no singing or vocals"
GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL = "whisper-large-v3-turbo"


def vocal_probability(vocal_score: float, instrumental_score: float, temperature: float = 0.05) -> float:
    """Softmax over the two CLAP prompt scores. Higher means more likely vocal."""
    top = max(vocal_score, instrumental_score)
    ev = math.exp((vocal_score - top) / temperature)
    ei = math.exp((instrumental_score - top) / temperature)
    return ev / (ev + ei)


def detect_vocals(db_path: Path, model_id: str, revision: str, selected_only: bool = True) -> dict:
    matrix, meta = load_matrix(db_path, model_id, revision, kind="sparse")
    model, processor, device = load_clap(model_id, revision)
    text_vecs = embed_texts(model, processor, device, [VOCAL_PROMPT, INSTRUMENTAL_PROMPT])
    scores = matrix @ text_vecs.T
    conn = dbmod.connect(db_path)
    selected_ids = None
    if selected_only:
        selected_ids = {r["id"] for r in conn.execute("SELECT id FROM tracks WHERE selected=1").fetchall()}
    updated = vocal_windows = 0
    for idx, row in enumerate(meta):
        if selected_ids is not None and row["track_id"] not in selected_ids:
            continue
        prob = vocal_probability(float(scores[idx, 0]), float(scores[idx, 1]))
        conn.execute("UPDATE windows SET vocal_prob=? WHERE id=?", (round(prob, 4), row["window_id"]))
        updated += 1
        if prob >= 0.5:
            vocal_windows += 1
    conn.commit()
    conn.close()
    return {"windows_scored": updated, "vocal_windows_at_0.5": vocal_windows}


def parse_transcription(payload: dict) -> dict:
    segments = payload.get("segments") or []
    logprobs = [s["avg_logprob"] for s in segments if "avg_logprob" in s]
    confidence = round(math.exp(sum(logprobs) / len(logprobs)), 4) if logprobs else None
    return {
        "text": (payload.get("text") or "").strip(),
        "language": payload.get("language"),
        "confidence": confidence,
    }


def groq_transcribe_file(path: Path, api_key: str, model: str = GROQ_MODEL) -> dict:
    boundary = "----music-discovery-boundary"
    body = bytearray()
    def field(name: str, value: str) -> None:
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    field("model", model)
    field("response_format", "verbose_json")
    body.extend(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\nContent-Type: audio/wav\r\n\r\n".encode()
    )
    body.extend(path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    request = urllib.request.Request(
        GROQ_URL,
        data=bytes(body),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return parse_transcription(json.loads(response.read().decode("utf-8")))


def extract_excerpt(track_path: Path, start: float, end: float, out: Path) -> Path:
    cmd = [
        "ffmpeg", "-y", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{max(end - start, 1):.3f}",
        "-i", str(track_path), "-ac", "1", "-ar", "16000", str(out),
    ]
    subprocess.run(cmd, capture_output=True, timeout=120, check=True)
    return out


def transcribe_vocals(db_path: Path, threshold: float = 0.5, selected_only: bool = True, limit: int | None = None) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set in this process environment")
    conn = dbmod.connect(db_path)
    selected_sql = "AND t.selected=1" if selected_only else ""
    rows = conn.execute(
        f"""SELECT w.id window_id, w.start_seconds, w.end_seconds, t.path
            FROM windows w JOIN tracks t ON t.id=w.track_id
            WHERE w.kind='sparse' AND w.vocal_prob>=? AND (w.lyric_text IS NULL OR w.lyric_text='') {selected_sql}
            ORDER BY w.vocal_prob DESC""",
        (threshold,),
    ).fetchall()
    if limit:
        rows = rows[:limit]
    done = errors = 0
    with tempfile.TemporaryDirectory() as tmp:
        for row in rows:
            excerpt = Path(tmp) / f"w{row['window_id']}.wav"
            try:
                extract_excerpt(Path(row["path"]), row["start_seconds"], row["end_seconds"], excerpt)
                result = groq_transcribe_file(excerpt, api_key)
                conn.execute(
                    "UPDATE windows SET lyric_text=?, lyric_language=?, lyric_confidence=?, lyric_source=? WHERE id=?",
                    (result["text"], result["language"], result["confidence"], f"groq:{GROQ_MODEL}", row["window_id"]),
                )
                conn.commit()
                done += 1
            except Exception as exc:  # per-window failure is recorded, never fatal to the batch
                conn.execute("UPDATE windows SET lyric_source=? WHERE id=?", (f"groq:error:{str(exc)[:120]}", row["window_id"]))
                conn.commit()
                errors += 1
    total = conn.execute("SELECT COUNT(*) c FROM windows WHERE lyric_text IS NOT NULL AND lyric_text != ''").fetchone()["c"]
    conn.close()
    return {"attempted": len(rows), "transcribed": done, "errors": errors, "windows_with_lyrics": total}
