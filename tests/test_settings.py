from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from music_discovery import config
from music_discovery.embed import resolve_device
from music_discovery.server import create_app
from music_discovery.settings import load_settings, model_status, save_settings


class FakeEngine:
    device = "fake"
    _model = None
    _matrix = None

    def search(self, query, top=20, include_lyrics=False, descriptions=None):
        return []


def test_device_resolution():
    assert resolve_device("auto", True) == "cuda"
    assert resolve_device("auto", False) == "cpu"
    assert resolve_device("cpu", True) == "cpu"
    assert resolve_device("cuda", False) == "cpu"


def test_settings_roundtrip_hides_key(tmp_path):
    save_settings({"device": "cpu", "meta_api_key": "secret-key"}, tmp_path)
    assert load_settings(tmp_path)["device"] == "cpu"

    client = TestClient(create_app(engine=FakeEngine(), db_path=tmp_path / "index" / "library.db"))
    got = client.get("/api/settings").json()
    assert got["meta_configured"] is True
    assert "secret-key" not in str(got)
    assert got["model"]["downloaded"] is True  # real cache on this machine

    assert client.post("/api/settings", json={"device": "bogus"}).status_code == 422
    posted = client.post("/api/settings", json={"device": "cuda"}).json()
    assert posted["device"] == "cuda"


def test_model_status_detects_weights(tmp_path):
    snapshot = (
        tmp_path / ("models--" + config.PRIMARY_MODEL_ID.replace("/", "--"))
        / "snapshots" / config.PRIMARY_MODEL_REVISION
    )
    snapshot.mkdir(parents=True)
    (snapshot / "pytorch_model.bin").write_bytes(b"x" * 200)
    small = model_status(tmp_path)
    assert small["downloaded"] is False  # tiny file is not a real checkpoint

    (snapshot / "pytorch_model.bin").write_bytes(b"x" * 100_000_001)
    big = model_status(tmp_path)
    assert big["downloaded"] is True
    assert big["size_bytes"] >= 100_000_001
