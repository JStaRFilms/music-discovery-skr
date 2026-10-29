import numpy as np
from fastapi.testclient import TestClient

from music_discovery import db as dbmod
from music_discovery.server import SearchEngine, create_app


class FakeEngine:
    device = "fake"

    def __init__(self):
        self.calls = []

    def search(self, query, top=5, include_lyrics=False):
        self.calls.append({"query": query, "top": top, "include_lyrics": include_lyrics})
        result = {
            "track_id": 1, "window_id": 1, "path": "/x/song.wav", "rel_path": "song.wav",
            "start_seconds": 10.0, "end_seconds": 20.0, "score": 0.5,
        }
        if include_lyrics:
            result = {**result, "sound_score": 0.4, "word_score": 0.3}
        return [result]


def _seed(db_path):
    conn = dbmod.connect(db_path)
    conn.execute(
        "INSERT INTO tracks(id,collection,path,rel_path,source_folder,size_bytes,mtime,duration_seconds,status) VALUES(1,'music','/x/song.wav','song.wav','(root)',1,0,100,'ok')"
    )
    conn.execute(
        "INSERT INTO windows(id,track_id,start_seconds,end_seconds,kind,lyric_text,lyric_trusted,lyric_confidence) "
        "VALUES(1,1,10,20,'sparse','when a man loves a woman',1,0.79)"
    )
    conn.commit()
    conn.close()


def test_status_search_feedback(tmp_path):
    db_path = tmp_path / "library.db"
    _seed(db_path)
    engine = FakeEngine()
    client = TestClient(create_app(engine=engine, db_path=db_path))

    status = client.get("/api/status").json()
    assert status["tracks_total"] == 1
    assert status["lyric_windows_trusted"] == 1

    found = client.post("/api/search", json={"query": "happy"}).json()
    assert found["results"][0]["file_name"] == "song.wav"
    assert found["results"][0]["excerpt_url"] == "/api/excerpt/1"
    assert found["results"][0]["track_url"] == "/api/track/1"
    assert found["results"][0]["lyric_trusted"] is True
    assert found["results"][0]["lyric_confidence"] == 0.79
    assert found["include_lyrics"] is False
    assert engine.calls[-1]["include_lyrics"] is False

    with_lyrics = client.post("/api/search", json={"query": "love", "include_lyrics": True}).json()
    assert with_lyrics["include_lyrics"] is True
    assert engine.calls[-1]["include_lyrics"] is True
    assert with_lyrics["results"][0]["sound_score"] == 0.4
    assert with_lyrics["results"][0]["word_score"] == 0.3

    bad = client.post("/api/feedback", json={"query_text": "happy", "track_id": 1, "mark": "great"})
    assert bad.status_code == 422

    ok = client.post("/api/feedback", json={"query_text": "happy", "track_id": 1, "window_id": 1, "mark": "usable"})
    assert ok.json() == {"ok": True}
    assert client.get("/api/status").json()["feedback_marks"] == 1


def test_track_file_serves_full_track_with_ranges(tmp_path):
    db_path = tmp_path / "library.db"
    song = tmp_path / "song.wav"
    song.write_bytes(b"0123456789abcdef")
    conn = dbmod.connect(db_path)
    conn.execute(
        "INSERT INTO tracks(id,collection,path,rel_path,source_folder,size_bytes,mtime,duration_seconds,status) VALUES(1,'music',?,'song.wav','(root)',16,0,100,'ok')",
        (str(song),),
    )
    conn.commit()
    conn.close()
    client = TestClient(create_app(engine=FakeEngine(), db_path=db_path))

    full = client.get("/api/track/1")
    assert full.status_code == 200
    assert full.content == b"0123456789abcdef"

    ranged = client.get("/api/track/1", headers={"Range": "bytes=4-7"})
    assert ranged.status_code == 206
    assert ranged.content == b"4567"

    assert client.get("/api/track/99").status_code == 404


def test_lyric_search_ranks_on_sound_and_words(tmp_path):
    engine = SearchEngine(db_path=tmp_path / "library.db")
    # Window 1 sounds right but its words do not; window 2 matches both.
    # Window 3 anchors the min-max ranges so the combined score can separate them.
    engine._matrix = np.array([[1.0, 0.0], [0.8, 0.6], [0.0, 1.0]], dtype=np.float32)
    engine._meta = [
        {"window_id": 1, "track_id": 1, "path": "/x/a.wav", "rel_path": "a.wav", "start_seconds": 0.0, "end_seconds": 10.0},
        {"window_id": 2, "track_id": 2, "path": "/x/b.wav", "rel_path": "b.wav", "start_seconds": 0.0, "end_seconds": 10.0},
        {"window_id": 3, "track_id": 3, "path": "/x/c.wav", "rel_path": "c.wav", "start_seconds": 0.0, "end_seconds": 10.0},
    ]
    engine._lyric_idx = [0, 1, 2]
    engine._lyric_vecs = np.array([[0.0, 1.0], [0.8, 0.6], [0.4, 0.9]], dtype=np.float32)

    results = engine._search_with_lyrics(np.array([1.0, 0.0], dtype=np.float32), top=2)

    assert [r["track_id"] for r in results] == [2, 1]
    assert results[0]["word_score"] > results[1]["word_score"]
