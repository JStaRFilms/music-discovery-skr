from __future__ import annotations

import hashlib
import mimetypes
import subprocess
from pathlib import Path

import numpy as np

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import config, db as dbmod
from .search import duplicate_groups, load_matrix, rank_tracks

EXCERPT_DIR = config.DATA_DIR / "cache" / "excerpts"


class SearchEngine:
    """Lazy CLAP search over the sparse full-library index. Loads once."""

    def __init__(self, db_path: Path = config.DB_PATH):
        self.db_path = db_path
        self._model = None
        self._matrix = None
        self._meta = None
        self._dup_groups: dict[int, int] = {}
        self._dense_cache: dict[int, object] = {}
        self._lyric_idx: list[int] | None = None
        self._lyric_vecs = None
        self._theme_vecs = None
        self._window_theme = None

    def _load(self):
        if self._matrix is not None:
            return
        from .embed import embed_texts, load_clap  # noqa: F401  (kept for symmetry)

        self._matrix, self._meta = load_matrix(
            self.db_path, config.PRIMARY_MODEL_ID, config.PRIMARY_MODEL_REVISION, kind="sparse"
        )
        self._dup_groups = duplicate_groups(self._matrix, self._meta)
        model, processor, device = load_clap(config.PRIMARY_MODEL_ID, config.PRIMARY_MODEL_REVISION)
        self._model = (model, processor, device)

    @property
    def device(self) -> str:
        return self._model[2] if self._model else "not loaded"

    # Personal taste: passages similar to ones John marked usable are
    # nudged up, similar-to-wrong nudged down. Small weights on purpose —
    # taste tilts the ranking, it does not replace the query match.
    TASTE_WEIGHTS = {"usable": 0.10, "close": 0.05, "wrong": -0.12}

    def _taste_adjustments(self):
        import numpy as np

        adj = np.zeros(len(self._meta), dtype=np.float32)
        row_of = {row["window_id"]: i for i, row in enumerate(self._meta)}
        conn = dbmod.connect(self.db_path)
        marks = conn.execute(
            "SELECT window_id, mark FROM judgements WHERE window_id IS NOT NULL AND mark IN ('usable','close','wrong')"
        ).fetchall()
        conn.close()
        by_mark: dict[str, list[int]] = {}
        for m in marks:
            if m["window_id"] in row_of:
                by_mark.setdefault(m["mark"], []).append(row_of[m["window_id"]])
        for mark, idxs in by_mark.items():
            sims = self._matrix @ self._matrix[idxs].T
            adj += self.TASTE_WEIGHTS[mark] * sims.max(axis=1)
        return adj, sum(len(v) for v in by_mark.values())

    def search(self, query: str, top: int = 20, include_lyrics: bool = False,
               descriptions: list[str] | None = None) -> list[dict]:
        from .embed import embed_texts

        self._load()
        model, processor, device = self._model
        texts = descriptions or [query]
        vecs = embed_texts(model, processor, device, texts)
        vec = vecs.mean(axis=0)
        vec = vec / max(float(np.linalg.norm(vec)), 1e-12)
        adj, _used = self._taste_adjustments()
        if not include_lyrics:
            return rank_tracks(self._matrix, self._meta, vec, top, adjustments=adj, groups=self._dup_groups)
        return self._search_with_lyrics(vec, top, adjustments=adj)

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

    def _theme_match(self, vec, lyric_vecs):
        """Soft theme agreement between the query and each window's lyrics.

        Theme vectors are the THEMES prompts from lyrics.py. The query's
        affinity to each theme weights the window's affinity to it, so a
        love-words query tilts toward love-labelled passages without any
        hard gate.
        """
        if self._model is None:
            return None
        if self._theme_vecs is None:
            from .embed import embed_texts
            from .lyrics import THEMES

            model, processor, device = self._model
            self._theme_vecs = embed_texts(model, processor, device, list(THEMES.values()))
            self._window_theme = lyric_vecs @ self._theme_vecs.T
        return self._window_theme @ (self._theme_vecs @ vec)

    def _search_with_lyrics(self, vec, top: int, adjustments=None) -> list[dict]:
        """Rank trusted-lyric windows by sound and words together (Tier 4 v3 method)."""
        import numpy as np

        from .lyric_search import _minmax

        idx, lyric_vecs = self._trusted_lyric_vectors()
        if not idx:
            return []
        sound = self._matrix[idx] @ vec
        words = lyric_vecs @ vec
        combined = _minmax(sound) + _minmax(words)
        theme_match = self._theme_match(vec, lyric_vecs)
        if theme_match is not None:
            combined = combined + 0.5 * _minmax(theme_match)
        if adjustments is not None:
            combined = combined + adjustments[idx]
        order = np.argsort(-combined)
        best: dict[int, dict] = {}
        for pos in order:
            row = self._meta[idx[int(pos)]]
            key = self._dup_groups.get(row["track_id"], row["track_id"])
            if key not in best:
                entry = {
                    **row,
                    "score": float(combined[int(pos)]),
                    "sound_score": float(sound[int(pos)]),
                    "word_score": float(words[int(pos)]),
                }
                if adjustments is not None:
                    entry["personal_adjustment"] = float(adjustments[idx[int(pos)]])
                if theme_match is not None:
                    entry["theme_score"] = float(theme_match[int(pos)])
                best[key] = entry
            if len(best) >= top:
                break
        return list(best.values())


    def refine_passage(self, query: str, track_id: int) -> dict:
        """Dense-scan one track (10s windows, 5s hop) for its best passage.

        On demand only: decoding and embedding a whole track takes seconds,
        so results are cached per track for the life of the server.
        """
        from .embed import decode_window, embed_audio, embed_texts
        from .windows import dense_windows

        self._load()
        conn = dbmod.connect(self.db_path)
        track = conn.execute("SELECT path, duration_seconds FROM tracks WHERE id=?", (track_id,)).fetchone()
        conn.close()
        if track is None or not track["duration_seconds"]:
            raise HTTPException(status_code=404, detail="track not found")
        if track_id not in self._dense_cache:
            wins = dense_windows(float(track["duration_seconds"]))
            if len(wins) > 600:
                raise HTTPException(status_code=422, detail="track too long for a dense scan")
            model, processor, device = self._model
            vecs = []
            for i in range(0, len(wins), 4):
                waves = [decode_window(Path(track["path"]), s, e - s) for s, e in wins[i:i + 4]]
                vecs.append(embed_audio(model, processor, device, waves))
            self._dense_cache[track_id] = (wins, np.vstack(vecs) if vecs else np.zeros((0, self._matrix.shape[1])))
        wins, dense_vecs = self._dense_cache[track_id]
        model, processor, device = self._model
        qvec = embed_texts(model, processor, device, [query])[0]
        scores = dense_vecs @ qvec
        best = int(np.argmax(scores)) if len(scores) else 0
        start, end = wins[best]
        return {"track_id": track_id, "start_seconds": start, "end_seconds": end,
                "score": float(scores[best]), "windows_scanned": len(wins)}


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
    # No model-side cap: cosine search over the local index can return any
    # count. 50 is a UI sanity bound, not a retrieval limit.
    top: int = Field(default=20, ge=1, le=50)
    include_lyrics: bool = False
    interpretation: str = "verbatim"


class RefineIn(BaseModel):
    query: str
    track_id: int


class SetupIn(BaseModel):
    root: str


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

    setup_state: dict = {"state": "idle", "root": None, "message": ""}

    @app.get("/api/setup/status")
    def setup_status():
        return setup_state

    @app.post("/api/setup/index")
    def setup_index(body: SetupIn):
        import threading

        root = Path(body.root.strip())
        if not root.is_dir():
            raise HTTPException(status_code=400, detail=f"folder not found: {root}")
        if setup_state["state"] in ("inventory", "indexing"):
            raise HTTPException(status_code=409, detail="indexing already running")

        def job():
            from .embed import run_index
            from .inventory import run_inventory

            try:
                setup_state.update(state="inventory", root=str(root), message="Scanning files…")
                counts = run_inventory(db_path, root)
                setup_state.update(state="indexing", message=f"Found {counts['audio']} audio files. Embedding passages…")
                result = run_index(db_path, config.PRIMARY_MODEL_ID, config.PRIMARY_MODEL_REVISION, all_tracks=True)
                engine._matrix = None  # force reload of the grown index
                engine._lyric_vecs = None
                engine._lyric_idx = None
                setup_state.update(state="done", message=f"Indexed {result['windows_embedded']} passages on {result['device']}.")
            except Exception as exc:  # surfaced to the UI, not swallowed
                setup_state.update(state="error", message=str(exc)[:500])

        threading.Thread(target=job, daemon=True).start()
        return {"ok": True, "state": "inventory"}

    @app.post("/api/refine")
    def refine(body: RefineIn):
        if not hasattr(engine, "refine_passage"):
            raise HTTPException(status_code=501, detail="refine not available")
        return engine.refine_passage(body.query.strip(), body.track_id)

    @app.post("/api/search")
    def search(body: SearchIn):
        from .provider import get_provider, interpretation_to_json, query_hash

        try:
            provider = get_provider(body.interpretation)
            interp = provider.interpret(body.query.strip())
        except (RuntimeError, NotImplementedError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        conn0 = dbmod.connect(db_path)
        conn0.execute(
            "INSERT OR IGNORE INTO interpretations(query_hash,query_text,provider,model,payload_json) VALUES(?,?,?,?,?)",
            (query_hash(body.query.strip()), body.query.strip(), interp.provider, interp.model,
             interpretation_to_json(interp)),
        )
        conn0.commit()
        conn0.close()
        results = engine.search(body.query.strip(), body.top, include_lyrics=body.include_lyrics,
                                descriptions=interp.descriptions)
        conn = dbmod.connect(db_path)
        out = []
        for r in results:
            win = conn.execute(
                "SELECT lyric_text, lyric_trusted, lyric_confidence, lyric_themes, vocal_prob FROM windows WHERE id=?", (r["window_id"],)
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
                "personal_adjustment": r.get("personal_adjustment"),
                "theme_score": r.get("theme_score"),
                "lyric_themes": [t for t in (win["lyric_themes"] or "").split(",") if t] if win else [],
                "lyric_text": win["lyric_text"] if win else None,
                "lyric_trusted": bool(win["lyric_trusted"]) if win and win["lyric_trusted"] is not None else None,
                "lyric_confidence": win["lyric_confidence"] if win else None,
                "vocal_prob": win["vocal_prob"] if win else None,
                "excerpt_url": f"/api/excerpt/{r['window_id']}",
                "track_url": f"/api/track/{r['track_id']}",
            })
        conn.close()
        mode = "sound + trusted words (local)" if body.include_lyrics else "verbatim (local)"
        return {"query": body.query, "interpretation": " ".join(interp.descriptions), "provider": mode,
                "interpretation_provider": interp.provider,
                "include_lyrics": body.include_lyrics, "results": out}

    @app.get("/api/excerpt/{window_id}")
    def excerpt(window_id: int):
        return FileResponse(excerpt_path(window_id, db_path), media_type="audio/wav")

    @app.get("/api/track/{track_id}")
    def track_file(track_id: int):
        conn = dbmod.connect(db_path)
        row = conn.execute("SELECT path FROM tracks WHERE id=?", (track_id,)).fetchone()
        conn.close()
        if row is None or not Path(row["path"]).exists():
            raise HTTPException(status_code=404, detail="track not found")
        # FileResponse answers Range requests, so the browser can seek and
        # start mid-track at the matched passage.
        media = mimetypes.guess_type(row["path"])[0] or "application/octet-stream"
        return FileResponse(row["path"], media_type=media)

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
