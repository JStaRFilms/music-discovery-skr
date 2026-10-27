from __future__ import annotations

import json
from pathlib import Path

# John's words stay verbatim. Sharpened variants are separate rows, never replacements.
QUERIES: list[dict] = [
    {"id": "t1-piano", "tier": 1, "text": "sparse solo piano, calm and unhurried", "held_out": False},
    {"id": "t1-strings", "tier": 1, "text": "driving strings, tense and urgent", "held_out": False},
    {"id": "t1-warm", "tier": 1, "text": "warm playful instrumental, not childish", "held_out": True},
    {"id": "t2-happy", "tier": 2, "text": "happy", "held_out": False, "john_verbatim": True},
    {"id": "t2-happy-fate", "tier": 2, "text": "happy with a twist of fate", "held_out": False},
    {"id": "t2-sad", "tier": 2, "text": "sad", "held_out": False, "john_verbatim": True},
    {"id": "t2-dramatic", "tier": 2, "text": "rather dramatic", "held_out": True, "john_verbatim": True},
    {"id": "t2-ginger", "tier": 2, "text": "slow-paced with a bit of ginger", "held_out": True, "john_verbatim": True},
    {"id": "t2-groove", "tier": 2, "text": "groove", "held_out": False, "john_verbatim": True},
    {"id": "t2-demure", "tier": 2, "text": "demure", "held_out": True, "john_verbatim": True},
    {"id": "t2-lost", "tier": 2, "text": "hopeful, but you can tell something has been lost", "held_out": False},
    {"id": "t3-reflective", "tier": 3, "text": "starts reflective and becomes determined", "held_out": False},
    {"id": "t3-quiet-tension", "tier": 3, "text": "quiet tension, no dramatic drums", "held_out": False},
    {"id": "t3-dialogue", "tier": 3, "text": "instrumental background for dialogue, with room for voices", "held_out": True},
    {"id": "t4-lyric-contrast", "tier": 4, "text": "sad words over an upbeat sound", "held_out": False},
]


def write_queries(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(QUERIES, indent=2), encoding="utf-8")
