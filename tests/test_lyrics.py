import math

from music_discovery.lyrics import assign_themes, classify_trust, parse_transcription, vocal_probability


def test_vocal_probability_directions():
    assert vocal_probability(0.5, 0.0) > 0.99
    assert vocal_probability(0.0, 0.5) < 0.01
    assert 0.4 < vocal_probability(0.3, 0.28) < 0.6


def test_parse_transcription_confidence():
    out = parse_transcription({
        "text": "  hello world again ",
        "language": "en",
        "segments": [{"avg_logprob": math.log(0.9), "no_speech_prob": 0.1}],
    })
    assert out["text"] == "hello world again"
    assert out["confidence"] == 0.9
    assert out["no_speech_prob"] == 0.1
    assert out["trusted"] is True


def test_parse_transcription_without_segments():
    out = parse_transcription({"text": "hi", "language": "en"})
    assert out["confidence"] is None


def test_classify_trust_rejects_artifacts_and_no_speech():
    assert classify_trust("Музыка", 0.9, 0.1) is False
    assert classify_trust("real sung words here", 0.9, 0.9) is False
    assert classify_trust("real sung words here", 0.4, 0.1) is False
    assert classify_trust("real sung words here", 0.9, 0.1) is True


def test_assign_themes_picks_strong_close_labels():
    assert assign_themes({"love": 0.81, "loss": 0.76, "party": 0.4}) == ["love", "loss"]
    assert assign_themes({"love": 0.44, "loss": 0.4}) == []
    assert assign_themes({}) == []
    assert assign_themes({"party": 0.9, "love": 0.88, "joy": 0.87}) == ["party", "love"]


def test_classify_trust_rejects_short_fragments():
    assert classify_trust("so", 0.52, 0.0) is False
    assert classify_trust("oh", 0.9, 0.1) is False
    assert classify_trust("thank you", 0.9, 0.1) is False
    assert classify_trust("happy birthday to", 0.9, 0.1) is True
