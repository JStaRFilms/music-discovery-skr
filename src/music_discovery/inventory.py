from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from . import db as dbmod

CANDIDATE_SUFFIXES = {".wav", ".mp3", ".aif", ".aiff", ".m4a", ".flac", ".ogg", ".mp4", ".mov", ""}


def probe(path: Path) -> dict | None:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_type,codec_name,sample_rate,channels:format=duration",
        "-of", "json", "--", str(path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception as exc:
        return {"error": str(exc)}
    if proc.returncode != 0:
        return {"error": (proc.stderr or "ffprobe failed")[:500]}
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        return {"error": f"bad ffprobe json: {exc}"}
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    if audio is None:
        return None
    duration = None
    try:
        duration = float(data.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        duration = None
    return {
        "codec": audio.get("codec_name"),
        "sample_rate": int(audio["sample_rate"]) if audio.get("sample_rate") else None,
        "channels": audio.get("channels"),
        "duration": duration,
    }


def source_folder(root: Path, path: Path) -> str:
    rel = path.relative_to(root)
    return str(rel.parent) if str(rel.parent) != "." else "(root)"


def run_inventory(db_path: Path, root: Path, collection: str = "music") -> dict:
    conn = dbmod.connect(db_path)
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in CANDIDATE_SUFFIXES)
    counts = {"seen": len(files), "audio": 0, "skipped": 0, "failed": 0}
    for path in files:
        info = probe(path)
        if info is None:
            counts["skipped"] += 1
            continue
        stat = path.stat()
        rel = str(path.relative_to(root))
        if "error" in info:
            counts["failed"] += 1
            status, error, dur = "failed", info["error"], None
            codec = sr = ch = None
        else:
            counts["audio"] += 1
            status, error = "ok", None
            dur, codec, sr, ch = info["duration"], info["codec"], info["sample_rate"], info["channels"]
            if not dur or dur <= 0:
                status, error = "failed", "zero or missing duration"
                counts["failed"] += 1
        conn.execute(
            """INSERT INTO tracks(collection,path,rel_path,source_folder,size_bytes,mtime,duration_seconds,codec,sample_rate,channels,status,error)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(path) DO UPDATE SET size_bytes=excluded.size_bytes,mtime=excluded.mtime,
                 duration_seconds=excluded.duration_seconds,codec=excluded.codec,
                 sample_rate=excluded.sample_rate,channels=excluded.channels,status=excluded.status,error=excluded.error""",
            (collection, str(path), rel, source_folder(root, path), stat.st_size, stat.st_mtime, dur, codec, sr, ch, status, error),
        )
        if counts["audio"] % 100 == 0:
            conn.commit()
            print(f"inventory: {counts}", file=sys.stderr)
    conn.commit()
    conn.close()
    return counts
