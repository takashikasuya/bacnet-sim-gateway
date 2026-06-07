"""EP-007.2 — /status /status/northbound /status/southbound endpoints (PR-F-054)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bbc_sim.observability.log_buffer import RingBufferLogHandler
from bbc_sim.rest.api import create_app
from bbc_sim.rest.status import StatusProvider
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list


@pytest.fixture
def served_status(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="bbc-test", device_id=9001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    bapp = build_application(cfg, with_network=False)
    handler = RingBufferLogHandler()
    status = StatusProvider(
        config=cfg, app=bapp, bound=False,
        get_manager=lambda: None, log_handler=handler,
    )
    client = TestClient(create_app(bapp, cfg, status=status))
    try:
        yield client, cfg, status
    finally:
        bapp.close()


def test_status_returns_mode_and_device(served_status):
    client, cfg, _ = served_status
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == cfg.mode.value
    assert data["object_count"] == len(cfg.objects)


def test_status_device_id_and_bbc_id_both_present(served_status):
    """ADR-003: device_id ≠ bbc_id must both appear and be distinguished."""
    client, cfg, _ = served_status
    resp = client.get("/status")
    device = resp.json()["device"]
    assert device["device_id"] == 9001
    assert device["bbc_id"] == "bbc-test"
    # they must not be equal for the test to be meaningful (ADR-003)
    assert str(device["device_id"]) != device["bbc_id"]


def test_status_503_without_provider(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    bapp = build_application(cfg, with_network=False)
    client = TestClient(create_app(bapp, cfg))
    try:
        assert client.get("/status").status_code == 503
        assert client.get("/status/northbound").status_code == 503
        assert client.get("/status/southbound").status_code == 503
    finally:
        bapp.close()


def test_northbound_status_structure(served_status):
    client, cfg, _ = served_status
    resp = client.get("/status/northbound")
    assert resp.status_code == 200
    data = resp.json()
    assert "bound" in data
    assert "bind_address" in data
    assert "port" in data
    assert "counters" in data
    counters = data["counters"]
    for key in ("who_is", "read_property", "write_property", "write_access_denied"):
        assert key in counters
        assert isinstance(counters[key], int)


def test_northbound_counters_start_at_zero(served_status):
    client, _, _ = served_status
    resp = client.get("/status/northbound")
    counters = resp.json()["counters"]
    for v in counters.values():
        assert v == 0


def test_southbound_status_no_manager(served_status):
    client, _, _ = served_status
    resp = client.get("/status/southbound")
    assert resp.status_code == 200
    data = resp.json()
    assert data["active"] is False
    assert data["protocols"] == []
    assert data["points"] == []


def test_status_uptime_seconds(served_status):
    client, _, _ = served_status
    resp = client.get("/status")
    data = resp.json()
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0
