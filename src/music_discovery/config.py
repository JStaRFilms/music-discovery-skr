from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Packaged installs set MUSIC_DISCOVERY_DATA to a writable per-user folder
# (e.g. %LOCALAPPDATA%\MusicDiscovery) so the index survives reinstalls.
DATA_DIR = Path(os.environ.get("MUSIC_DISCOVERY_DATA", PROJECT_ROOT / "data"))
INDEX_DIR = DATA_DIR / "index"
DB_PATH = INDEX_DIR / "library.db"
MANIFEST_DIR = INDEX_DIR / "manifests"

DEFAULT_MUSIC_ROOT = Path(r"E:\Assets\Audio\Music")
DEFAULT_SFX_ROOT = Path(r"E:\Assets\Audio\SFX")

PRIMARY_MODEL_ID = "laion/larger_clap_music_and_speech"
PRIMARY_MODEL_REVISION = "195c3a3e68faebb3e2088b9a79e79b43ddbda76b"
COMPARATOR_MODEL_ID = "laion/clap-htsat-fused"
COMPARATOR_MODEL_REVISION = "365dea6ef167def6676140ed93bbc43f84dabb28"
# Rejected 2026-10-27: laion/larger_clap_music @ a0b4534a14f58e20944452dff00a22a06ce629d1
# produced near-identical text vectors for unrelated prompts (cosine 0.998-0.999,
# measured). Its text tower collapses on this stack; do not re-select it without
# re-running the model health check. See experiments/RUN-2026-10-27.md.

SAMPLE_RATE = 48000
WINDOW_SECONDS = 10
SPARSE_FRACTIONS = (0.10, 0.30, 0.50, 0.70, 0.90)
EDGE_GUARD_SECONDS = 5.0


def ensure_dirs() -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
