"""EP-007.5 — POST /mode returns restart_required and leaves config.mode unchanged."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bbc_sim.models import RuntimeMode
from bbc_sim.rest.api import create_app
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list


@pytest.fixture
def mode_client(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    cfg.mode = RuntimeMode.simulator
    bapp = build_application(cfg, with_network=False)
    client = TestClient(create_app(bapp, cfg))
    try:
        yield client, cfg
    finally:
        bapp.close()


def test_mode_endpoint_returns_restart_required(mode_client):
    client, cfg = mode_client
    resp = client.post("/mode", json={"mode": "gateway"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["applied"] is False
    assert data["restart_required"] is True


def test_mode_endpoint_does_not_change_config_mode(mode_client):
    """POST /mode must not mutate config.mode (live mode switch is future work)."""
    client, cfg = mode_client
    original = cfg.mode
    client.post("/mode", json={"mode": "gateway"})
    assert cfg.mode == original


def test_mode_endpoint_returns_current_and_requested(mode_client):
    client, cfg = mode_client
    resp = client.post("/mode", json={"mode": "combined"})
    data = resp.json()
    assert data["current_mode"] == cfg.mode.value
    assert data["requested_mode"] == "combined"


def test_mode_endpoint_hint_contains_mode(mode_client):
    client, _ = mode_client
    resp = client.post("/mode", json={"mode": "gateway"})
    hint = resp.json().get("hint", "")
    assert "gateway" in hint
