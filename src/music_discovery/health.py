from __future__ import annotations

import numpy as np

from .embed import embed_texts, load_clap

PROBE_TEXTS = [
    "the sound of a cat meowing",
    "heavy metal drums and electric guitar",
    "sparse solo piano, calm and unhurried",
    "driving strings, tense and urgent",
    "happy",
    "sad",
]
MAX_PAIRWISE_COSINE = 0.90


def max_pairwise_cosine(vectors: np.ndarray) -> float:
    sims = vectors @ vectors.T
    n = len(vectors)
    off = [float(sims[i, j]) for i in range(n) for j in range(i + 1, n)]
    return max(off) if off else 0.0


def check_model(model_id: str, revision: str) -> dict:
    model, processor, device = load_clap(model_id, revision)
    vectors = embed_texts(model, processor, device, PROBE_TEXTS)
    worst = max_pairwise_cosine(vectors)
    return {
        "model": model_id,
        "revision": revision,
        "device": device,
        "max_pairwise_cosine": round(worst, 4),
        "threshold": MAX_PAIRWISE_COSINE,
        "healthy": bool(worst < MAX_PAIRWISE_COSINE),
    }
