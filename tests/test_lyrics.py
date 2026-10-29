import math

from music_discovery.lyrics import parse_transcription, vocal_probability


def test_vocal_probability_directions():
    assert vocal_probability(0.5, 0.0) > 0.99
    assert vocal_probability(0.0, 0.5) < 0.01
    assert 0.4 < vocal_probability(0.3, 0.28) < 0.6


def test_parse_transcription_confidence():
    out = parse_transcription({
        "text": "  hello world ",
        "language": "en",
        "segments": [{"avg_logprob": math.log(0.9)}, {"avg_logprob": math.log(0.9)}],
    })
    assert out == {"text": "hello world", "language": "en", "confidence": 0.9}


def test_parse_transcription_without_segments():
    out = parse_transcription({"text": "hi", "language": "en"})
    assert out["confidence"] is None
