"""EP-007.3 — /bindings and southbound status (PR-F-055)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from bbc_sim.models import BindingDirection, BindingSpec
from bbc_sim.rest.api import create_app
from bbc_sim.rest.status import StatusProvider
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.southbound.binding import SouthboundManager
from bbc_sim.southbound.transport import InMemoryTransport
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list


@pytest.fixture
def bound_config(sample_pointlist, free_port):
    """Config with one object wired to an InMemoryTransport binding."""
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="bbc-gw", device_id=7001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    # attach a binding to the first analog object
    obj = next(o for o in cfg.objects if not o.binding)
    obj.binding = BindingSpec(
        protocol="mqtt",
        direction=BindingDirection.telemetry,
        address="test/telemetry",
    )
    return cfg


@pytest.fixture
def with_manager(bound_config):
    bapp = build_application(bound_config, with_network=False)
    transport = InMemoryTransport()
    manager = SouthboundManager(bapp, bound_config, transport)
    status = StatusProvider(
        config=bound_config,
        app=bapp,
        bound=False,
        get_manager=lambda: manager,
    )
    client = TestClient(create_app(bapp, bound_config, status=status))
    try:
        yield client, manager, transport, bound_config
    finally:
        bapp.close()


def test_bindings_endpoint_no_manager(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    bapp = build_application(cfg, with_network=False)
    status = StatusProvider(config=cfg, app=bapp, bound=False, get_manager=lambda: None)
    client = TestClient(create_app(bapp, cfg, status=status))
    try:
        resp = client.get("/bindings")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        bapp.close()


def test_bindings_returns_points_with_manager(with_manager):
    client, manager, _, cfg = with_manager
    # Transport not started yet — status() still returns data from manager
    resp = client.get("/bindings")
    assert resp.status_code == 200
    data = resp.json()
    bound_ids = {p["point_id"] for p in data}
    bound_spec = next(o for o in cfg.objects if o.binding)
    assert bound_spec.point_id in bound_ids


def test_bindings_quality_unknown_before_telemetry(with_manager):
    client, _, _, _ = with_manager
    resp = client.get("/bindings")
    data = resp.json()
    for point in data:
        assert point["quality"] == "unknown"
        assert point["last_update_ts"] is None


def test_bindings_quality_good_after_telemetry(with_manager):
    """After feeding a valid telemetry payload, quality becomes 'good'."""
    import asyncio

    from bbc_sim.southbound.binding import channels as sb_channels

    client, manager, transport, cfg = with_manager
    bound = next(o for o in cfg.objects if o.binding)
    tele_channel, _ = sb_channels(bound)

    async def _run() -> None:
        await manager.start()
        payload = json.dumps(25.5).encode()
        await transport.feed(tele_channel, payload)
        await manager.stop()

    asyncio.run(_run())

    sb = manager.status()
    rec = next(p for p in sb["points"] if p["point_id"] == bound.point_id)
    assert rec["quality"] == "good"
    assert rec["last_update_ts"] is not None


def test_southbound_status_with_manager(with_manager):
    client, _, _, _ = with_manager
    resp = client.get("/status/southbound")
    assert resp.status_code == 200
    data = resp.json()
    assert data["active"] is True
    assert len(data["protocols"]) >= 1
    assert len(data["points"]) >= 1
