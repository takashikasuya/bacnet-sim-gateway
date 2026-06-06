"""Transport abstraction for southbound protocols (ADR-013).

The binding logic depends only on this Protocol, so MQTT/ZeroMQ/gRPC are
interchangeable. ``InMemoryTransport`` is the self-contained default used by tests and
for CI without external brokers; concrete protocol transports live alongside it.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

Handler = Callable[[str, bytes], Awaitable[None]]


@runtime_checkable
class Transport(Protocol):
    """Publish/subscribe transport. Channels are protocol-specific strings."""

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def subscribe(self, channel: str, handler: Handler) -> None: ...

    async def publish(self, channel: str, payload: bytes) -> None: ...


class InMemoryTransport:
    """In-process pub/sub fake. Deterministic, no network — ideal for tests."""

    def __init__(self) -> None:
        self._subs: dict[str, list[Handler]] = defaultdict(list)
        self.published: list[tuple[str, bytes]] = []
        self._started = False

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False

    def subscribe(self, channel: str, handler: Handler) -> None:
        self._subs[channel].append(handler)

    async def publish(self, channel: str, payload: bytes) -> None:
        self.published.append((channel, payload))
        for handler in self._subs.get(channel, []):
            await handler(channel, payload)

    async def feed(self, channel: str, payload: bytes) -> None:
        """Test helper: simulate an inbound message from the field side."""
        for handler in self._subs.get(channel, []):
            await handler(channel, payload)
