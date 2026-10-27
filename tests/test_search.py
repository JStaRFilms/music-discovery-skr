import numpy as np

from music_discovery.search import rank_tracks


def test_rank_groups_by_track_and_keeps_best_window():
    matrix = np.array([[1.0, 0.0], [0.9, 0.0], [0.0, 1.0]], dtype=np.float32)
    meta = [
        {"row_index": 0, "window_id": 1, "track_id": 1, "start_seconds": 0, "end_seconds": 10, "path": "a", "rel_path": "a"},
        {"row_index": 1, "window_id": 2, "track_id": 1, "start_seconds": 10, "end_seconds": 20, "path": "a", "rel_path": "a"},
        {"row_index": 2, "window_id": 3, "track_id": 2, "start_seconds": 0, "end_seconds": 10, "path": "b", "rel_path": "b"},
    ]
    out = rank_tracks(matrix, meta, np.array([1.0, 0.0], dtype=np.float32), top_tracks=2)
    assert [r["track_id"] for r in out] == [1, 2]
    assert out[0]["window_id"] == 1
