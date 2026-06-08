"""EP-008.11 (#70) — GatewayEgressClient.run_forever reconnect/stop loop (no grpc).

The wire round-trip is covered by the integration loopback; here we drive the
reconnect-with-backoff and stop-event logic with a stubbed ``_connect_and_serve`` so it
runs in the default (grpc-free) suite.
"""

from __future__ import annotations

import asyncio

from bbc_sim.bows.downlink.client import GatewayEgressClient
from bbc_sim.bows.downlink.executor import CommandExecutor
from bbc_sim.bows.downlink.models import EgressConfig


def _client(fake_bacnet_app) -> GatewayEgressClient:
    config = EgressConfig(endpoint="bos:443", gateway_id="gw-1", target="t", tls=False)
    return GatewayEgressClient(config, executor=CommandExecutor(fake_bacnet_app(), "t"))


async def test_run_forever_reconnects_then_stops(monkeypatch, fake_bacnet_app) -> None:
    # Zero-delay backoff so the test doesn't actually sleep between attempts.
    monkeypatch.setattr(
        "bbc_sim.bows.downlink.client.reconnect_delays", lambda **kw: iter([0.0] * 100)
    )
    client = _client(fake_bacnet_app)
    stop = asyncio.Event()
    calls: list[int] = []

    async def fake_connect() -> None:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("stream dropped")  # first attempt fails -> must reconnect
        stop.set()  # second attempt succeeds and asks to stop

    client._connect_and_serve = fake_connect  # type: ignore[method-assign]
    await asyncio.wait_for(client.run_forever(stop), timeout=2)

    assert len(calls) == 2  # reconnected after the failure


async def test_run_forever_does_not_connect_when_stopped_upfront(fake_bacnet_app) -> None:
    client = _client(fake_bacnet_app)
    stop = asyncio.Event()
    stop.set()
    calls: list[int] = []

    async def fake_connect() -> None:
        calls.append(1)

    client._connect_and_serve = fake_connect  # type: ignore[method-assign]
    await asyncio.wait_for(client.run_forever(stop), timeout=2)

    assert calls == []


async def test_run_forever_closes_bacnet_client_on_exit(fake_bacnet_app) -> None:
    client = _client(fake_bacnet_app)
    closed: list[bool] = []

    class _App:
        def close(self) -> None:
            closed.append(True)

    client._app = _App()  # simulate a self-built BACnet client
    stop = asyncio.Event()

    async def fake_connect() -> None:
        stop.set()

    client._connect_and_serve = fake_connect  # type: ignore[method-assign]
    await asyncio.wait_for(client.run_forever(stop), timeout=2)

    assert closed == [True]  # BACnet client closed in finally
