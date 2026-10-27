from music_discovery.windows import dense_windows, sparse_windows


def test_sparse_covers_track_scattered():
    wins = sparse_windows(180.0)
    assert len(wins) == 5
    assert wins[0][0] < 30
    assert wins[-1][0] > 140
    assert all(e - s <= 10.0 for s, e in wins)


def test_sparse_short_track_single_window():
    wins = sparse_windows(8.0)
    assert wins == [(0.0, 8.0)]


def test_sparse_zero_duration():
    assert sparse_windows(0) == []


def test_dense_contiguous():
    wins = dense_windows(32.0, hop=5.0)
    assert wins[0] == (0.0, 10.0)
    assert wins[-1][1] == 32.0
