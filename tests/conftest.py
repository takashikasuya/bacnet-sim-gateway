"""Shared test fixtures."""

from __future__ import annotations

import asyncio
import socket
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _current_loop_for_sync_tests(request):
    """Give sync tests a current event loop.

    bacpypes3 object construction schedules a coroutine via ``ensure_future`` and so
    needs a current loop. Async tests get one from pytest-asyncio; sync tests that build
    objects (e.g. fault/engine/REST) would otherwise fail depending on run order.
    """
    if asyncio.iscoroutinefunction(request.function):
        yield
        return
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield
    finally:
        # Cancel and drain any tasks bacpypes3 scheduled during object construction
        # so we don't leak "Task was destroyed but it is pending" warnings.
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture
def sample_pointlist() -> Path:
    """Path to the 29-column SBCO sample point list."""
    return FIXTURES / "sample_pointlist.csv"


class FakeBacnetApp:
    """Records write_property calls; matches the bacpypes3 Application signature used by
    the down-link executor (services.client.write_property). For grpc-free unit tests."""

    def __init__(self, fail: Exception | None = None) -> None:
        self.calls: list[tuple[object, ...]] = []
        self._fail = fail

    async def write_property(
        self, target: str, objid: str, prop: str, value: object, priority: int | None = None
    ) -> None:
        self.calls.append((target, objid, prop, value, priority))
        if self._fail is not None:
            raise self._fail

    def close(self) -> None:  # pragma: no cover - parity with the real client
        pass


@pytest.fixture
def fake_bacnet_app() -> type[FakeBacnetApp]:
    """Return the FakeBacnetApp class so tests can construct one (optionally failing)."""
    return FakeBacnetApp


def free_udp_port() -> int:
    """Pick a free UDP port for loopback BACnet tests."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def free_port():
    """Return the free_udp_port helper (callable) for tests needing several ports."""
    return free_udp_port
