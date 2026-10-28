import numpy as np

from music_discovery import db as dbmod
from music_discovery.search import load_matrix


def test_load_matrix_filters_by_kind(tmp_path):
    db_path = tmp_path / "library.db"
    conn = dbmod.connect(db_path)
    conn.execute(
        "INSERT INTO tracks(id,collection,path,rel_path,source_folder,size_bytes,mtime,status) VALUES(1,'music','/x/a.wav','a.wav','(root)',1,0,'ok')"
    )
    for wid, kind in [(1, "sparse"), (2, "dense")]:
        conn.execute(
            "INSERT INTO windows(id,track_id,start_seconds,end_seconds,kind) VALUES(?,?,0,10,?)", (wid, 1, kind)
        )
        conn.execute(
            "INSERT INTO embeddings(window_id,model_id,model_revision,dim,row_index) VALUES(?,'m','r',2,?)",
            (wid, wid - 1),
        )
    conn.commit()
    conn.close()
    np.save(tmp_path / "embeddings-m.npy", np.eye(2, dtype=np.float32))

    sparse_matrix, sparse_meta = load_matrix(db_path, "m", "r", kind="sparse")
    dense_matrix, dense_meta = load_matrix(db_path, "m", "r", kind="dense")
    assert len(sparse_meta) == 1 and sparse_meta[0]["window_id"] == 1
    assert len(dense_meta) == 1 and dense_meta[0]["window_id"] == 2
    assert sparse_matrix.shape == (1, 2)
