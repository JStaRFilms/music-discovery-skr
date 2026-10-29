from fastapi.testclient import TestClient

from music_discovery import db as dbmod
from music_discovery.server import create_app


class FakeEngine:
    device = "fake"

    def search(self, query, top=5):
        return [{
            "track_id": 1, "window_id": 1, "path": "/x/song.wav", "rel_path": "song.wav",
            "start_seconds": 10.0, "end_seconds": 20.0, "score": 0.5,
        }]


def _seed(db_path):
    conn = dbmod.connect(db_path)
    conn.execute(
        "INSERT INTO tracks(id,collection,path,rel_path,source_folder,size_bytes,mtime,duration_seconds,status) VALUES(1,'music','/x/song.wav','song.wav','(root)',1,0,100,'ok')"
    )
    conn.execute("INSERT INTO windows(id,track_id,start_seconds,end_seconds,kind) VALUES(1,1,10,20,'sparse')")
    conn.commit()
    conn.close()


def test_status_search_feedback(tmp_path):
    db_path = tmp_path / "library.db"
    _seed(db_path)
    client = TestClient(create_app(engine=FakeEngine(), db_path=db_path))

    status = client.get("/api/status").json()
    assert status["tracks_total"] == 1

    found = client.post("/api/search", json={"query": "happy"}).json()
    assert found["results"][0]["file_name"] == "song.wav"
    assert found["results"][0]["excerpt_url"] == "/api/excerpt/1"

    bad = client.post("/api/feedback", json={"query_text": "happy", "track_id": 1, "mark": "great"})
    assert bad.status_code == 422

    ok = client.post("/api/feedback", json={"query_text": "happy", "track_id": 1, "window_id": 1, "mark": "usable"})
    assert ok.json() == {"ok": True}
    assert client.get("/api/status").json()["feedback_marks"] == 1
