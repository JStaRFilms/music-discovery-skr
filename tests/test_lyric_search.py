import numpy as np

from music_discovery.lyric_search import _minmax


def test_minmax_scales_and_handles_constant():
    out = _minmax(np.array([2.0, 4.0, 6.0]))
    assert out.tolist() == [0.0, 0.5, 1.0]
    assert _minmax(np.array([3.0, 3.0])).tolist() == [0.0, 0.0]
