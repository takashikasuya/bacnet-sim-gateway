"""EP-009.8 — MqttTransport unit tests (paho client mocked, no broker)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bbc_sim.southbound.mqtt import MqttTransport


@pytest.fixture
def transport():
    t = MqttTransport("broker.example", 1883)
    t._client = MagicMock()  # replace paho client; no network
    return t


def test_subscribe_registers_and_calls_client(transport):
    async def handler(channel: str, payload: bytes) -> None:
        return None

    transport.subscribe("telemetry/x", handler)
    assert handler in transport._handlers["telemetry/x"]
    transport._client.subscribe.assert_called_once_with("telemetry/x")


async def test_publish_forwards_to_client(transport):
    await transport.publish("cmd/y", b"payload")
    transport._client.publish.assert_called_once_with("cmd/y", b"payload")


async def test_on_message_dispatches_to_handler_on_loop(transport):
    received: list[tuple[str, bytes]] = []
    done = asyncio.Event()

    async def handler(channel: str, payload: bytes) -> None:
        received.append((channel, payload))
        done.set()

    transport.subscribe("telemetry/x", handler)
    transport._loop = asyncio.get_running_loop()  # set by start() in production

    msg = SimpleNamespace(topic="telemetry/x", payload=b"hello")
    transport._on_message(None, None, msg)  # called from paho's thread in production
    # Deterministic wait for the loop to drain run_coroutine_threadsafe.
    await asyncio.wait_for(done.wait(), timeout=1.0)

    assert received == [("telemetry/x", b"hello")]


async def test_on_message_without_loop_is_noop(transport):
    handler_called = False

    async def handler(channel: str, payload: bytes) -> None:
        nonlocal handler_called
        handler_called = True

    transport.subscribe("telemetry/x", handler)
    transport._loop = None  # start() not called yet

    msg = SimpleNamespace(topic="telemetry/x", payload=b"hello")
    transport._on_message(None, None, msg)  # returns synchronously, schedules nothing
    assert handler_called is False


async def test_on_message_unknown_topic_is_noop(transport):
    handler = MagicMock()
    transport.subscribe("telemetry/x", handler)
    transport._loop = asyncio.get_running_loop()

    msg = SimpleNamespace(topic="telemetry/UNKNOWN", payload=b"x")
    transport._on_message(None, None, msg)  # no matching handler -> schedules nothing
    handler.assert_not_called()
