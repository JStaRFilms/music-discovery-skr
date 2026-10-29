from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY,
    collection TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    rel_path TEXT NOT NULL,
    source_folder TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    mtime REAL NOT NULL,
    duration_seconds REAL,
    codec TEXT,
    sample_rate INTEGER,
    channels INTEGER,
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT,
    selected INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS windows (
    id INTEGER PRIMARY KEY,
    track_id INTEGER NOT NULL REFERENCES tracks(id),
    start_seconds REAL NOT NULL,
    end_seconds REAL NOT NULL,
    kind TEXT NOT NULL,
    vocal_prob REAL,
    lyric_text TEXT,
    lyric_language TEXT,
    lyric_confidence REAL,
    lyric_source TEXT,
    no_speech_prob REAL,
    lyric_trusted INTEGER,
    UNIQUE(track_id, start_seconds, kind)
);
CREATE TABLE IF NOT EXISTS embeddings (
    window_id INTEGER NOT NULL REFERENCES windows(id),
    model_id TEXT NOT NULL,
    model_revision TEXT NOT NULL,
    dim INTEGER NOT NULL,
    row_index INTEGER NOT NULL,
    PRIMARY KEY (window_id, model_id, model_revision)
);
CREATE TABLE IF NOT EXISTS interpretations (
    query_hash TEXT PRIMARY KEY,
    query_text TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS judgements (
    id INTEGER PRIMARY KEY,
    query_id TEXT NOT NULL,
    anon_id TEXT NOT NULL,
    track_id INTEGER NOT NULL,
    window_id INTEGER,
    mark TEXT,
    timestamp_ok INTEGER,
    failure_class TEXT,
    notes TEXT
);
CREATE VIRTUAL TABLE IF NOT EXISTS lyrics_fts USING fts5(window_id, lyric_text);
CREATE INDEX IF NOT EXISTS idx_windows_track ON windows(track_id);
CREATE INDEX IF NOT EXISTS idx_tracks_selected ON tracks(selected);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(windows)").fetchall()}
    for col, ddl in (("no_speech_prob", "REAL"), ("lyric_trusted", "INTEGER")):
        if col not in cols:
            conn.execute(f"ALTER TABLE windows ADD COLUMN {col} {ddl}")
    conn.commit()
    return conn
