from __future__ import annotations

import subprocess
import time
from pathlib import Path

import numpy as np

from . import db as dbmod
from .config import SAMPLE_RATE, WINDOW_SECONDS
from .windows import sparse_windows

TARGET_SAMPLES = SAMPLE_RATE * WINDOW_SECONDS


def decode_window(path: Path, start: float, seconds: float = WINDOW_SECONDS) -> np.ndarray:
    cmd = [
        "ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{seconds:.3f}",
        "-i", str(path), "-ac", "1", "-ar", str(SAMPLE_RATE),
        "-f", "f32le", "-acodec", "pcm_f32le", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or b"ffmpeg decode failed").decode("utf-8", "replace")[:500])
    audio = np.frombuffer(proc.stdout, dtype=np.float32).copy()
    if audio.size < TARGET_SAMPLES:
        audio = np.pad(audio, (0, TARGET_SAMPLES - audio.size))
    return audio[:TARGET_SAMPLES]


def load_clap(model_id: str, revision: str):
    import torch
    from transformers import AutoProcessor, ClapModel

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ClapModel.from_pretrained(model_id, revision=revision).to(device)
    model.eval()
    processor = AutoProcessor.from_pretrained(model_id, revision=revision)
    return model, processor, device


def features_to_numpy(feats) -> np.ndarray:
    """Unwrap a Transformers feature output to a normalized float32 array.

    Transformers v5 returns BaseModelOutputWithPooling (pooler_output holds
    the projected vector); older versions return a bare tensor.
    """
    tensor = feats if hasattr(feats, "detach") else feats.pooler_output
    arr = tensor.detach().cpu().numpy().astype(np.float32)
    return arr / np.maximum(np.linalg.norm(arr, axis=1, keepdims=True), 1e-12)


def embed_texts(model, processor, device: str, texts: list[str]) -> np.ndarray:
    import torch

    inputs = processor(text=texts, return_tensors="pt", padding=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        feats = model.get_text_features(**inputs)
    return features_to_numpy(feats)


def embed_audio(model, processor, device: str, waves: list[np.ndarray]) -> np.ndarray:
    import torch

    inputs = processor(audio=waves, sampling_rate=SAMPLE_RATE, return_tensors="pt", padding=True)
    inputs = {k: v.to(device) if hasattr(v, "to") else v for k, v in inputs.items()}
    with torch.no_grad():
        feats = model.get_audio_features(**inputs)
    return features_to_numpy(feats)


def run_index(db_path: Path, model_id: str, revision: str, limit_tracks: int | None = None, batch: int = 4) -> dict:
    conn = dbmod.connect(db_path)
    tracks = conn.execute("SELECT * FROM tracks WHERE selected=1 AND status='ok' ORDER BY id").fetchall()
    if limit_tracks:
        tracks = tracks[:limit_tracks]
    out_path = db_path.parent / f"embeddings-{model_id.replace('/', '_')}.npy"
    existing = np.load(out_path) if out_path.exists() else np.empty((0, 512), dtype=np.float32)
    rows: list[np.ndarray] = [r for r in existing]
    next_row = len(rows)

    model, processor, device = load_clap(model_id, revision)
    started = time.time()
    n_windows = 0
    for track in tracks:
        wins = sparse_windows(float(track["duration_seconds"]))
        waves, win_ids = [], []
        for start, end in wins:
            cur = conn.execute(
                "INSERT OR IGNORE INTO windows(track_id,start_seconds,end_seconds,kind) VALUES(?,?,?, 'sparse')",
                (track["id"], start, end),
            )
            wid = conn.execute(
                "SELECT id FROM windows WHERE track_id=? AND start_seconds=? AND kind='sparse'",
                (track["id"], start),
            ).fetchone()["id"]
            already = conn.execute(
                "SELECT 1 FROM embeddings WHERE window_id=? AND model_id=? AND model_revision=?",
                (wid, model_id, revision),
            ).fetchone()
            if already:
                continue
            waves.append(decode_window(Path(track["path"]), start, end - start))
            win_ids.append(wid)
        for i in range(0, len(waves), batch):
            chunk = embed_audio(model, processor, device, waves[i : i + batch])
            for vec, wid in zip(chunk, win_ids[i : i + batch]):
                if len(rows) <= next_row:
                    rows.append(vec)
                else:
                    rows[next_row] = vec
                conn.execute(
                    "INSERT OR REPLACE INTO embeddings(window_id,model_id,model_revision,dim,row_index) VALUES(?,?,?,?,?)",
                    (wid, model_id, revision, int(vec.shape[0]), next_row),
                )
                next_row += 1
                n_windows += 1
        conn.commit()
        np.save(out_path, np.stack(rows) if rows else existing)
        print(f"indexed track {track['id']} windows+={len(waves)} total_rows={next_row}")
    elapsed = max(time.time() - started, 1e-9)
    conn.close()
    return {"device": device, "windows_embedded": n_windows, "seconds": round(elapsed, 2),
            "windows_per_second": round(n_windows / elapsed, 3) if n_windows else 0.0,
            "embeddings_path": str(out_path)}
