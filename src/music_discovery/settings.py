from __future__ import annotations

import json
from pathlib import Path

from . import config

DEFAULTS = {"device": "auto", "meta_api_key": "", "interpretation": "verbatim"}
DEVICE_CHOICES = ("auto", "cuda", "cpu")


def settings_path(data_dir: Path | None = None) -> Path:
    return (data_dir or config.DATA_DIR) / "settings.json"


def load_settings(data_dir: Path | None = None) -> dict:
    path = settings_path(data_dir)
    if not path.exists():
        return dict(DEFAULTS)
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULTS)
    return {**DEFAULTS, **{k: saved[k] for k in DEFAULTS if k in saved}}


def save_settings(updates: dict, data_dir: Path | None = None) -> dict:
    current = load_settings(data_dir)
    for key in DEFAULTS:
        if key in updates and updates[key] is not None:
            current[key] = updates[key]
    if current["device"] not in DEVICE_CHOICES:
        current["device"] = "auto"
    path = settings_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return current


def public_settings(saved: dict) -> dict:
    """Settings safe to send to the UI. The API key itself never leaves."""
    return {
        "device": saved["device"],
        "interpretation": saved["interpretation"],
        "meta_configured": bool(saved["meta_api_key"]),
    }


def model_cache_dir() -> Path:
    try:
        from huggingface_hub.constants import HF_HUB_CACHE

        return Path(HF_HUB_CACHE)
    except Exception:
        return Path.home() / ".cache" / "huggingface" / "hub"


def model_status(cache_dir: Path | None = None) -> dict:
    """Whether the pinned CLAP checkpoint is on disk, and how big it is."""
    cache = cache_dir or model_cache_dir()
    repo = cache / ("models--" + config.PRIMARY_MODEL_ID.replace("/", "--"))
    snapshot = repo / "snapshots" / config.PRIMARY_MODEL_REVISION
    size = 0
    weights = False
    if snapshot.exists():
        for f in snapshot.rglob("*"):
            if f.is_file():
                try:
                    real_size = f.resolve().stat().st_size
                    size += real_size
                    if f.suffix in (".bin", ".safetensors") and real_size > 100_000_000:
                        weights = True
                except OSError:
                    continue
    return {
        "model": config.PRIMARY_MODEL_ID,
        "revision": config.PRIMARY_MODEL_REVISION,
        "downloaded": weights,
        "size_bytes": size,
    }
