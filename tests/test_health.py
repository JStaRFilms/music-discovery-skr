import numpy as np

from music_discovery.health import max_pairwise_cosine


def test_max_pairwise_cosine_distinct_vectors():
    vecs = np.eye(3, dtype=np.float32)
    assert max_pairwise_cosine(vecs) == 0.0


def test_max_pairwise_cosine_collapsed_vectors():
    vecs = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    assert max_pairwise_cosine(vecs) == 1.0
