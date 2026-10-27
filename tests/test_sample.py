import sqlite3

from music_discovery.sample import bucket


class Row(dict):
    pass


def _row(folder):
    r = Row()
    r["source_folder"] = folder
    return r


def test_bucket_rules():
    assert bucket(_row(r"Stream Beats\Lofi")) == "streambeats"
    assert bucket(_row("Pixabay")) == "pixabay"
    assert bucket(_row("(root)")) == "root"
    assert bucket(_row("Church")) == "longtail"


def test_schema_has_lyrics_track(tmp_path):
    from music_discovery import db as dbmod

    conn = dbmod.connect(tmp_path / "t.db")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(windows)").fetchall()}
    assert {"vocal_prob", "lyric_text", "lyric_confidence", "lyric_source"} <= cols
    conn.execute("SELECT * FROM lyrics_fts LIMIT 1")
    conn.close()
