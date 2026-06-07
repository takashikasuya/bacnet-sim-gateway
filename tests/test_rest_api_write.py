"""EP-009.9 — REST mutating endpoints: error paths and scenario branches (PR-F-050, §17)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bbc_sim.rest.api import create_app
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list


@pytest.fixture
def client(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    app = build_application(cfg, with_network=False)
    c = TestClient(create_app(app, cfg))
    try:
        yield c
    finally:
        app.close()


# ---- /objects/{id}/write ----


def test_write_unknown_point_returns_404(client):
    assert client.post("/objects/NOPE/write", json={"value": 1.0}).status_code == 404


def test_write_non_writable_returns_409(client):
    # PT001 is an analogInput (writable=False)
    assert client.post("/objects/PT001/write", json={"value": 1.0}).status_code == 409


def test_write_invalid_value_type_returns_400(client):
    # PT006 is writable analogValue; a non-numeric value must be rejected, not 500.
    r = client.post("/objects/PT006/write", json={"value": "not-a-number"})
    assert r.status_code == 400


def test_write_valid_value_returns_updated_view(client):
    r = client.post("/objects/PT006/write", json={"value": 21.0})
    assert r.status_code == 200
    assert r.json()["present_value"] == 21.0


# ---- /simulation/scenario ----


def test_scenario_unknown_point_returns_404(client):
    r = client.post("/simulation/scenario", json={"point_id": "NOPE", "fault": "freeze"})
    assert r.status_code == 404


def test_scenario_abnormal_with_explicit_value(client):
    r = client.post(
        "/simulation/scenario",
        json={"point_id": "PT006", "fault": "abnormal", "value": 123.0},
    )
    assert r.status_code == 200
    assert r.json()["present_value"] == 123.0


def test_scenario_clear_resets_out_of_service(client):
    # Put PT001 out of service, then clear it.
    client.post("/simulation/scenario", json={"point_id": "PT001", "fault": "out_of_service"})
    r = client.post("/simulation/scenario", json={"point_id": "PT001", "fault": "clear"})
    assert r.status_code == 200
    assert r.json()["out_of_service"] is False


def test_scenario_direct_value_without_fault(client):
    # No fault, just a value -> sets present-value on a writable point.
    r = client.post("/simulation/scenario", json={"point_id": "PT006", "value": 7.5})
    assert r.status_code == 200
    assert r.json()["present_value"] == 7.5
