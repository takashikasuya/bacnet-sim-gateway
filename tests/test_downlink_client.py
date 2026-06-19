"""EP-008.11 (#70) — GatewayEgressClient.run_forever reconnect/stop loop (no grpc).

The wire round-trip is covered by the integration loopback; here we drive the
reconnect-with-backoff and stop-event logic with a stubbed ``_connect_and_serve`` so it
runs in the default (grpc-free) suite.
"""

from __future__ import annotations

import asyncio

import pytest

from bbc_sim.bows.downlink.client import GatewayEgressClient, _mtls_pems
from bbc_sim.bows.downlink.executor import CommandExecutor
from bbc_sim.bows.downlink.models import EgressConfig
from bbc_sim.bows.point_registry import PointRegistry


def _client(fake_bacnet_app) -> GatewayEgressClient:
    config = EgressConfig(endpoint="bos:443", gateway_id="gw-1", target="t", tls=False)
    return GatewayEgressClient(
        config, executor=CommandExecutor(fake_bacnet_app(), "t", point_registry=PointRegistry([]))
    )


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


async def test_run_forever_builds_no_bacnet_client_when_stopped_upfront() -> None:
    # No injected executor: a stop set before the loop must not bind a UDP socket.
    config = EgressConfig(endpoint="bos:443", gateway_id="gw-1", target="t", tls=False)
    client = GatewayEgressClient(config)
    stop = asyncio.Event()
    stop.set()
    await asyncio.wait_for(client.run_forever(stop), timeout=2)
    assert client._app is None  # never built a BACnet client


async def test_run_forever_propagates_cancellation(fake_bacnet_app) -> None:
    client = _client(fake_bacnet_app)
    stop = asyncio.Event()

    async def fake_connect() -> None:
        raise asyncio.CancelledError()  # service shutdown mid-connect

    client._connect_and_serve = fake_connect  # type: ignore[method-assign]
    with pytest.raises(asyncio.CancelledError):
        await client.run_forever(stop)


def test_mtls_pems_requires_cert_and_key(monkeypatch) -> None:
    for var in ("BOWS_EGRESS_TLS_CERT", "BOWS_EGRESS_TLS_KEY", "BOWS_EGRESS_TLS_CA"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(RuntimeError, match="mTLS requires"):
        _mtls_pems()


def test_mtls_pems_loads_pems_when_set(monkeypatch, tmp_path) -> None:
    cert, key = tmp_path / "cert.pem", tmp_path / "key.pem"
    cert.write_bytes(b"CERT")
    key.write_bytes(b"KEY")
    monkeypatch.setenv("BOWS_EGRESS_TLS_CERT", str(cert))
    monkeypatch.setenv("BOWS_EGRESS_TLS_KEY", str(key))
    monkeypatch.delenv("BOWS_EGRESS_TLS_CA", raising=False)
    ca, cert_pem, key_pem = _mtls_pems()
    assert ca is None and cert_pem == b"CERT" and key_pem == b"KEY"  # CA optional


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
