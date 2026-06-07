"""EP-009.7 — ZmqTransport unit tests (no real sockets/broker)."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from bbc_sim.southbound.zeromq import ZmqTransport


@pytest.fixture
def transport():
    t = ZmqTransport("tcp://127.0.0.1:5599", "tcp://127.0.0.1:5598")
    try:
        yield t
    finally:
        t._sub.close()
        t._pub.close()


async def test_dispatch_routes_to_subscribed_handler(transport):
    received: list[tuple[str, bytes]] = []

    async def handler(channel: str, payload: bytes) -> None:
        received.append((channel, payload))

    transport.subscribe("telemetry/x", handler)
    await transport._dispatch([b"telemetry/x", b"payload-1"])
    assert received == [("telemetry/x", b"payload-1")]


async def test_dispatch_ignores_unsubscribed_channel(transport):
    handler = AsyncMock()
    transport.subscribe("telemetry/x", handler)
    await transport._dispatch([b"other/channel", b"p"])
    handler.assert_not_awaited()


@pytest.mark.parametrize("frames", [[b"only-one"], [b"a", b"b", b"c"], []])
async def test_dispatch_skips_malformed_multipart(transport, caplog, frames):
    handler = AsyncMock()
    transport.subscribe("telemetry/x", handler)
    with caplog.at_level(logging.WARNING, logger="bbc_sim.southbound.zeromq"):
        await transport._dispatch(frames)  # must not raise
    handler.assert_not_awaited()
    assert any("malformed multipart" in r.getMessage() for r in caplog.records)


async def test_publish_sends_multipart_frames(transport):
    # MagicMock keeps .close() synchronous for fixture teardown; only the awaited
    # send_multipart needs to be async.
    transport._pub = MagicMock()
    transport._pub.send_multipart = AsyncMock()
    await transport.publish("cmd/y", b"do-it")
    transport._pub.send_multipart.assert_awaited_once_with([b"cmd/y", b"do-it"])


async def test_subscribe_registers_handler(transport):
    async def handler(channel: str, payload: bytes) -> None:
        return None

    transport.subscribe("a/b", handler)
    assert handler in transport._handlers["a/b"]
