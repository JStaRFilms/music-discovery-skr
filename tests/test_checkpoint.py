import numpy as np

from music_discovery.embed import save_checkpoint


def test_save_checkpoint_roundtrip_and_replace(tmp_path):
    out = tmp_path / "emb.npy"
    save_checkpoint([np.ones(4, dtype=np.float32)], out)
    assert np.load(out).shape == (1, 4)
    save_checkpoint([np.ones(4, dtype=np.float32), np.zeros(4, dtype=np.float32)], out)
    loaded = np.load(out)
    assert loaded.shape == (2, 4)
    assert not (tmp_path / "emb.tmp.npy").exists()
