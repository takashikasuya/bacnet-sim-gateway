"""EP-008.11 (#70) — reconnect backoff with jitter (pure)."""

from __future__ import annotations

import random

from bbc_sim.bows.downlink.backoff import reconnect_delays


class _HalfRng:
    """random() == 0.5 -> the symmetric jitter term is exactly 0."""

    def random(self) -> float:
        return 0.5


def test_base_sequence_without_jitter_is_exponential_capped() -> None:
    delays = reconnect_delays(base=1.0, factor=2.0, cap=30.0, jitter=0.2, rng=_HalfRng())
    assert [next(delays) for _ in range(7)] == [1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 30.0]


def test_jitter_stays_within_fraction_of_base() -> None:
    rng = random.Random(1234)
    delays = reconnect_delays(base=1.0, factor=2.0, cap=30.0, jitter=0.2, rng=rng)
    first = [next(delays) for _ in range(5)]
    bases = [1.0, 2.0, 4.0, 8.0, 16.0]
    for value, base in zip(first, bases, strict=True):
        assert base * 0.8 <= value <= base * 1.2


def test_delays_are_never_negative() -> None:
    delays = reconnect_delays(base=0.5, factor=3.0, cap=10.0, jitter=1.0, rng=random.Random(0))
    assert all(next(delays) >= 0.0 for _ in range(50))
