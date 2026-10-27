import numpy as np
import torch

from music_discovery.embed import features_to_numpy


class _Output:
    def __init__(self, tensor):
        self.pooler_output = tensor
        self.last_hidden_state = None


def test_features_to_numpy_unwraps_pooler_output():
    out = features_to_numpy(_Output(torch.tensor([[3.0, 4.0]])))
    assert out.shape == (1, 2)
    assert np.allclose(out, [[0.6, 0.8]], atol=1e-6)


def test_features_to_numpy_accepts_bare_tensor():
    out = features_to_numpy(torch.tensor([[0.0, 2.0]]))
    assert np.allclose(out, [[0.0, 1.0]], atol=1e-6)
