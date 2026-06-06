"""Deterministic value generators for simulator mode (requirements §11, PR-F-030).

Each generator maps a time ``t`` (seconds) to a presentValue. random_walk is seeded by
point_id so runs are reproducible (re-generation is deterministic, like the YAML).
"""

from __future__ import annotations

import math
import random
from typing import Any

from bbc_sim.models import BacnetObjectSpec


class ValueGenerator:
    def __init__(self, spec: BacnetObjectSpec) -> None:  # noqa: B027 - base ctor
        self.spec = spec

    def next(self, t: float) -> Any:
        """Return the presentValue at time t."""
        raise NotImplementedError


def _bounds(spec: BacnetObjectSpec) -> tuple[float, float]:
    lo = spec.min_pres_value if spec.min_pres_value is not None else 0.0
    hi = spec.max_pres_value if spec.max_pres_value is not None else 100.0
    return float(lo), float(hi)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(value, hi))


class RandomWalk(ValueGenerator):
    def __init__(self, spec: BacnetObjectSpec) -> None:
        self._lo, self._hi = _bounds(spec)
        step = float(spec.update.params.get("step", 1.0))
        self._step = step
        self._rng = random.Random(spec.point_id)  # deterministic per point
        start = spec.present_value if isinstance(spec.present_value, (int, float)) else None
        self._value = float(start) if start is not None else (self._lo + self._hi) / 2

    def next(self, t: float) -> float:
        self._value = _clamp(
            self._value + self._rng.uniform(-self._step, self._step), self._lo, self._hi
        )
        return round(self._value, 4)


class Sinusoidal(ValueGenerator):
    def __init__(self, spec: BacnetObjectSpec) -> None:
        self._lo, self._hi = _bounds(spec)
        self._period = float(spec.update.params.get("period", 60.0))
        if self._period <= 0:
            raise ValueError(f"{spec.point_id}: sinusoidal period must be > 0")

    def next(self, t: float) -> float:
        mid = (self._lo + self._hi) / 2
        amp = (self._hi - self._lo) / 2
        return round(mid + amp * math.sin(2 * math.pi * t / self._period), 4)


class Replay(ValueGenerator):
    def __init__(self, spec: BacnetObjectSpec) -> None:
        seq = list(spec.update.params.get("sequence", []))
        if not seq:
            raise ValueError(f"{spec.point_id}: replay requires a non-empty 'sequence'")
        self._seq = seq
        self._i = 0

    def next(self, t: float) -> Any:
        value = self._seq[self._i % len(self._seq)]
        self._i += 1
        return value


class Scenario(ValueGenerator):
    def __init__(self, spec: BacnetObjectSpec) -> None:
        pts = spec.update.params.get("setpoints", [])
        # normalize to sorted (time, value) pairs
        self._setpoints = sorted(((float(tp), v) for tp, v in pts), key=lambda x: x[0])
        if not self._setpoints:
            raise ValueError(f"{spec.point_id}: scenario requires 'setpoints'")

    def next(self, t: float) -> Any:
        current = self._setpoints[0][1]
        for tp, value in self._setpoints:
            if t >= tp:
                current = value
            else:
                break
        return current


_GENERATORS: dict[str, type[ValueGenerator]] = {
    "random_walk": RandomWalk,
    "sinusoidal": Sinusoidal,
    "replay": Replay,
    "scenario": Scenario,
}


def make_generator(spec: BacnetObjectSpec) -> ValueGenerator | None:
    """Build the generator for an object, or None if no update mode is set."""
    mode = spec.update.mode
    if not mode:
        return None
    try:
        cls = _GENERATORS[mode]
    except KeyError:
        raise ValueError(f"unknown update mode: {mode!r}") from None
    return cls(spec)
