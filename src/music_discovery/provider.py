from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Protocol


@dataclass
class Interpretation:
    descriptions: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    mode: str = "simultaneous"  # simultaneous | temporal | plain
    provider: str = "noop"
    model: str | None = None


class InterpretationProvider(Protocol):
    name: str

    def interpret(self, query: str) -> Interpretation: ...


class NoOpProvider:
    """Verbatim only. The offline default. Never bills."""

    name = "noop"

    def interpret(self, query: str) -> Interpretation:
        return Interpretation(descriptions=[query], provider=self.name)


class MetaSparkProvider:
    """Meta muse-spark-1.3 query interpretation. Stub until an API key is configured.

    Only query text is sent. No audio, paths, or filenames. Responses must be
    cached by the caller via `interpretations` so a phrase never bills twice.
    """

    name = "meta"
    model = "muse-spark-1.3"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    def interpret(self, query: str) -> Interpretation:
        if not self.api_key:
            raise RuntimeError("MetaSparkProvider needs an API key; use NoOpProvider offline")
        raise NotImplementedError("Wire the Meta Model API call here; keep NoOp as the control")


class LocalProvider:
    """Placeholder for a local model on John's machine (same interface, no network)."""

    name = "local"

    def interpret(self, query: str) -> Interpretation:
        raise NotImplementedError("Local model not configured yet")


def query_hash(query: str) -> str:
    return hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()


def interpretation_to_json(interp: Interpretation) -> str:
    return json.dumps(asdict(interp), ensure_ascii=False)
