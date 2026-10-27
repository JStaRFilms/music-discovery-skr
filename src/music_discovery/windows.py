from __future__ import annotations

from .config import EDGE_GUARD_SECONDS, SPARSE_FRACTIONS, WINDOW_SECONDS


def sparse_windows(duration: float) -> list[tuple[float, float]]:
    if duration <= 0:
        return []
    out: list[tuple[float, float]] = []
    seen: set[float] = set()
    for frac in SPARSE_FRACTIONS:
        centre = frac * duration
        start = centre - WINDOW_SECONDS / 2
        start = max(EDGE_GUARD_SECONDS, min(start, max(EDGE_GUARD_SECONDS, duration - WINDOW_SECONDS)))
        if duration <= WINDOW_SECONDS:
            start = 0.0
        start = round(start, 3)
        if start in seen:
            continue
        seen.add(start)
        out.append((start, round(min(start + WINDOW_SECONDS, duration), 3)))
    return out


def dense_windows(duration: float, hop: float = 5.0) -> list[tuple[float, float]]:
    if duration <= 0:
        return []
    out: list[tuple[float, float]] = []
    start = 0.0
    while start < duration:
        out.append((round(start, 3), round(min(start + WINDOW_SECONDS, duration), 3)))
        if start + WINDOW_SECONDS >= duration:
            break
        start += hop
    return out
