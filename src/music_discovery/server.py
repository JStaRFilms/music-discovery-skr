from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import config, db as dbmod
from .search import load_matrix, rank_tracks

EXCERPT_DIR = config.DATA_DIR / "cache" / "excerpts"


class SearchEngine:
    """Lazy CLAP search over the sparse full-library index. Loads once."""

    def __init__(self, db_path: Path = config.DB_PATH):
        self.db_path = db_path
        self._model = None
        self._matrix = None
        self._meta = None
        self._lyric_idx: list[int] | None = None
        self._lyric_vecs = None

    def _load(self):
        if self._matrix is not None:
            return
        from .embed import embed_texts, load_clap  # noqa: F401  (kept for symmetry)

        self._matrix, self._meta = load_matrix(
            self.db_path, config.PRIMARY_MODEL_ID, config.PRIMARY_MODEL_REVISION, kind="sparse"
        )
        model, processor, device = load_clap(config.PRIMARY_MODEL_ID, config.PRIMARY_MODEL_REVISION)
        self._model = (model, processor, device)

    @property
    def device(self) -> str:
        return self._model[2] if self._model else "not loaded"

    def search(self, query: str, top: int = 5, include_lyrics: bool = False) -> list[dict]:
        from .embed import embed_texts

        self._load()
        model, processor, device = self._model
        vec = embed_texts(model, processor, device, [query])[0]
        if not include_lyrics:
            return rank_tracks(self._matrix, self._meta, vec, top)
        return self._search_with_lyrics(vec, top)

    def _trusted_lyric_vectors(self):
        """CLAP text vectors for trusted lyric windows, embedded once and cached."""
        if self._lyric_vecs is not None:
            return self._lyric_idx, self._lyric_vecs
        from .embed import embed_texts

        conn = dbmod.connect(self.db_path)
        trusted = {
            r["window_id"]: r["lyric_text"]
            for r in conn.execute(
                "SELECT w.id window_id, w.lyric_text FROM windows w "
                "WHERE w.lyric_trusted=1 AND w.lyric_text IS NOT NULL AND w.lyric_text != ''"
            ).fetchall()
        }
        conn.close()
        model, processor, device = self._model
        self._lyric_idx = [i for i, row in enumerate(self._meta) if row["window_id"] in trusted]
        texts = [trusted[self._meta[i]["window_id"]][:300] for i in self._lyric_idx]
        vecs = []
        for start in range(0, len(texts), 64):
            vecs.append(embed_texts(model, processor, device, texts[start:start + 64]))
        import numpy as np

        self._lyric_vecs = np.vstack(vecs) if vecs else np.zeros((0, self._matrix.shape[1]), dtype=np.float32)
        return self._lyric_idx, self._lyric_vecs

    def _search_with_lyrics(self, vec, top: int) -> list[dict]:
        """Rank trusted-lyric windows by sound and words together (Tier 4 v3 method)."""
        import numpy as np

        from .lyric_search import _minmax

        idx, lyric_vecs = self._trusted_lyric_vectors()
        if not idx:
            return []
        sound = self._matrix[idx] @ vec
        words = lyric_vecs @ vec
        combined = _minmax(sound) + _minmax(words)
        order = np.argsort(-combined)
        best: dict[int, dict] = {}
        for pos in order:
            row = self._meta[idx[int(pos)]]
            if row["track_id"] not in best:
                best[row["track_id"]] = {
                    **row,
                    "score": float(combined[int(pos)]),
                    "sound_score": float(sound[int(pos)]),
                    "word_score": float(words[int(pos)]),
                }
            if len(best) >= top:
                break
        return list(best.values())


class FeedbackIn(BaseModel):
    query_text: str
    track_id: int
    window_id: int | None = None
    mark: str
    timestamp_ok: bool | None = None
    failure_class: str | None = None
    notes: str | None = None


class SearchIn(BaseModel):
    query: str
    top: int = 5
    include_lyrics: bool = False


def excerpt_path(window_id: int, db_path: Path) -> Path:
    EXCERPT_DIR.mkdir(parents=True, exist_ok=True)
    out = EXCERPT_DIR / f"w{window_id}.wav"
    if out.exists():
        return out
    conn = dbmod.connect(db_path)
    row = conn.execute(
        "SELECT w.start_seconds, w.end_seconds, t.path FROM windows w JOIN tracks t ON t.id=w.track_id WHERE w.id=?",
        (window_id,),
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="window not found")
    cmd = [
        "ffmpeg", "-y", "-v", "error", "-ss", f"{row['start_seconds']:.3f}",
        "-t", f"{max(row['end_seconds'] - row['start_seconds'], 1):.3f}",
        "-i", row["path"], "-ac", "1", "-ar", "48000", str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=120)
    if proc.returncode != 0 or not out.exists():
        raise HTTPException(status_code=500, detail="excerpt extraction failed")
    return out


def create_app(engine: SearchEngine | None = None, db_path: Path = config.DB_PATH) -> FastAPI:
    app = FastAPI(title="Music Discovery (local)")
    engine = engine or SearchEngine(db_path)

    @app.get("/api/status")
    def status():
        conn = dbmod.connect(db_path)
        tracks = conn.execute("SELECT COUNT(*) c FROM tracks WHERE status='ok'").fetchone()["c"]
        covered = conn.execute(
            """SELECT COUNT(DISTINCT w.track_id) c FROM embeddings e JOIN windows w ON w.id=e.window_id
               WHERE e.model_id=? AND w.kind='sparse'""",
            (config.PRIMARY_MODEL_ID,),
        ).fetchone()["c"]
        windows = conn.execute(
            """SELECT COUNT(*) c FROM embeddings e JOIN windows w ON w.id=e.window_id
               WHERE e.model_id=? AND w.kind='sparse'""",
            (config.PRIMARY_MODEL_ID,),
        ).fetchone()["c"]
        feedback = conn.execute("SELECT COUNT(*) c FROM judgements WHERE mark IS NOT NULL AND mark != ''").fetchone()["c"]
        lyric_windows = conn.execute(
            "SELECT COUNT(*) c FROM windows WHERE lyric_trusted=1 AND lyric_text IS NOT NULL AND lyric_text != ''"
        ).fetchone()["c"]
        conn.close()
        return {
            "model": config.PRIMARY_MODEL_ID,
            "device": engine.device,
            "tracks_indexed": covered,
            "tracks_total": tracks,
            "sparse_windows": windows,
            "feedback_marks": feedback,
            "lyric_windows_trusted": lyric_windows,
            "audio_leaves_machine": False,
        }

    @app.post("/api/search")
    def search(body: SearchIn):
        results = engine.search(body.query.strip(), body.top, include_lyrics=body.include_lyrics)
        conn = dbmod.connect(db_path)
        out = []
        for r in results:
            win = conn.execute(
                "SELECT lyric_text, lyric_trusted, lyric_confidence, vocal_prob FROM windows WHERE id=?", (r["window_id"],)
            ).fetchone()
            track = conn.execute(
                "SELECT duration_seconds FROM tracks WHERE id=?", (r["track_id"],)
            ).fetchone()
            out.append({
                "track_id": r["track_id"],
                "window_id": r["window_id"],
                "file_name": Path(r["path"]).name,
                "rel_path": r["rel_path"],
                "start_seconds": r["start_seconds"],
                "end_seconds": r["end_seconds"],
                "duration_seconds": track["duration_seconds"] if track else None,
                "score": r["score"],
                "sound_score": r.get("sound_score"),
                "word_score": r.get("word_score"),
                "lyric_text": win["lyric_text"] if win else None,
                "lyric_trusted": bool(win["lyric_trusted"]) if win and win["lyric_trusted"] is not None else None,
                "lyric_confidence": win["lyric_confidence"] if win else None,
                "vocal_prob": win["vocal_prob"] if win else None,
                "excerpt_url": f"/api/excerpt/{r['window_id']}",
            })
        conn.close()
        mode = "sound + trusted words (local)" if body.include_lyrics else "verbatim (local)"
        return {"query": body.query, "interpretation": body.query, "provider": mode,
                "include_lyrics": body.include_lyrics, "results": out}

    @app.get("/api/excerpt/{window_id}")
    def excerpt(window_id: int):
        return FileResponse(excerpt_path(window_id, db_path), media_type="audio/wav")

    @app.post("/api/feedback")
    def feedback(body: FeedbackIn):
        if body.mark not in ("usable", "close", "wrong"):
            raise HTTPException(status_code=422, detail="mark must be usable, close, or wrong")
        qid = "ui-" + hashlib.sha256(body.query_text.strip().lower().encode()).hexdigest()[:10]
        conn = dbmod.connect(db_path)
        conn.execute(
            "INSERT INTO judgements(query_id,anon_id,track_id,window_id,mark,timestamp_ok,failure_class,notes) VALUES(?,?,?,?,?,?,?,?)",
            (qid, f"W{body.window_id}", body.track_id, body.window_id, body.mark,
             None if body.timestamp_ok is None else int(body.timestamp_ok), body.failure_class, body.notes),
        )
        conn.commit()
        conn.close()
        return {"ok": True}

    dist = Path(__file__).resolve().parents[2] / "web" / "dist"
    if dist.exists():
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=dist, html=True), name="static")
    return app


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
