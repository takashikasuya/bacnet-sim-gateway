"""#73 — GatewayIngress gRPC uplink client (no grpc, unit tests)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from bbc_sim.bows.models import BowsConfig, Reading
from bbc_sim.bows.point_registry import PointRegistry
from bbc_sim.bows.uplink.client import GatewayIngressClient, IngressConfig
from bbc_sim.models import BacnetObjectSpec, BacnetObjectType


def _spec(point_id: str, object_type: BacnetObjectType, instance: int) -> BacnetObjectSpec:
    return BacnetObjectSpec(
        point_id=point_id, object_type=object_type, object_instance=instance, object_name=point_id
    )


_REGISTRY = PointRegistry(
    [
        _spec("pt-ai-1", BacnetObjectType.analogInput, 1),
        _spec("pt-bv-3", BacnetObjectType.binaryValue, 3),
    ]
)
_TS = datetime(2025, 6, 1, 0, 0, 0, tzinfo=UTC)


def test_ingress_config_defaults() -> None:
    cfg = IngressConfig(endpoint="bos:50051", gateway_id="gw-1", point_registry=_REGISTRY)
    assert cfg.tls is True
    assert cfg.keepalive_s == 20.0
    assert cfg.local_address is None


def test_ingress_config_requires_point_registry() -> None:
    cfg = IngressConfig(endpoint="e", gateway_id="g", point_registry=_REGISTRY)
    assert cfg.point_registry is _REGISTRY


async def test_run_forever_stops_immediately_when_stop_set() -> None:
    cfg = IngressConfig(
        endpoint="bos:50051", gateway_id="gw-1", point_registry=_REGISTRY, tls=False
    )
    client = GatewayIngressClient(cfg)
    stop = asyncio.Event()
    stop.set()
    calls: list[int] = []

    async def fake_connect() -> None:  # pragma: no cover
        calls.append(1)

    client._connect_and_serve = fake_connect  # type: ignore[method-assign]
    await asyncio.wait_for(client.run_forever(stop), timeout=2)
    assert calls == []


async def test_run_forever_reconnects_on_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        "bbc_sim.bows.uplink.client.reconnect_delays", lambda **kw: iter([0.0] * 100)
    )
    cfg = IngressConfig(
        endpoint="bos:50051", gateway_id="gw-1", point_registry=_REGISTRY, tls=False
    )
    client = GatewayIngressClient(cfg)
    stop = asyncio.Event()
    calls: list[int] = []

    async def fake_connect() -> None:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("transport error")
        stop.set()

    client._connect_and_serve = fake_connect  # type: ignore[method-assign]
    await asyncio.wait_for(client.run_forever(stop), timeout=2)
    assert len(calls) == 2


async def test_run_forever_propagates_cancellation() -> None:
    cfg = IngressConfig(
        endpoint="bos:50051", gateway_id="gw-1", point_registry=_REGISTRY, tls=False
    )
    client = GatewayIngressClient(cfg)
    stop = asyncio.Event()

    async def fake_connect() -> None:
        raise asyncio.CancelledError()

    client._connect_and_serve = fake_connect  # type: ignore[method-assign]
    with pytest.raises(asyncio.CancelledError):
        await client.run_forever(stop)
