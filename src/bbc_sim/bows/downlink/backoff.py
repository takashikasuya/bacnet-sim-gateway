"""Reconnect backoff with jitter (pure, ADR-017).

Bounded exponential backoff with symmetric jitter, used between GatewayEgress stream
reconnect attempts so a fleet of gateways doesn't reconnect in lockstep. Pure and
deterministic under an injected ``rng`` for unit testing.
"""

from __future__ import annotations

import random
from collections.abc import Iterator


def reconnect_delays(
    *,
    base: float = 1.0,
    factor: float = 2.0,
    cap: float = 30.0,
    jitter: float = 0.2,
    rng: random.Random | None = None,
) -> Iterator[float]:
    """Yield an unbounded sequence of reconnect delays (seconds).

    Delay n is ``min(cap, base*factor**n)`` perturbed by +/-``jitter`` fraction, clamped
    to >= 0. With ``rng`` seeded (or its ``random`` returning 0.5) the jitter term is 0,
    giving the deterministic base sequence.
    """
    draw = (rng or random).random
    attempt = 0
    while True:
        raw = min(cap, base * (factor**attempt))
        delay = raw + raw * jitter * (2.0 * draw() - 1.0)
        yield max(0.0, delay)
        attempt += 1
