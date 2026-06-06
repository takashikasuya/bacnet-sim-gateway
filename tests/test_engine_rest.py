"""EP-003.1/.2/.5 — simulation engine + REST control plane (PR-F-030/031/050, §17)."""

from __future__ import annotations

import pytest
from bacpypes3.primitivedata import ObjectIdentifier
from fastapi.testclient import TestClient

from bbc_sim.models import UpdateConfig
from bbc_sim.rest.api import create_app
from bbc_sim.simulation.engine import SimulationEngine
from bbc_sim.simulation.fault import FaultController, FaultType
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list


@pytest.fixture
def served(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    # drive PT001 (AI) with a sinusoid
    ai = next(o for o in cfg.objects if o.point_id == "PT001")
    ai.update = UpdateConfig(interval=1, mode="sinusoidal", params={"period": 10.0})
    app = build_application(cfg, with_network=False)
    faults = FaultController()
    try:
        yield app, cfg, faults, ai
    finally:
        app.close()


def test_engine_tick_drives_present_value(served):
    app, cfg, faults, ai = served
    engine = SimulationEngine(app, cfg, faults)
    oid = ObjectIdentifier(("analogInput", ai.object_instance))
    engine.tick(2.5)
    v1 = float(app.get_object_id(oid).presentValue)
    engine.tick(7.5)
    v2 = float(app.get_object_id(oid).presentValue)
    assert v1 != v2  # value moves over time


def test_engine_skips_frozen_object(served):
    app, cfg, faults, ai = served
    engine = SimulationEngine(app, cfg, faults)
    oid = ObjectIdentifier(("analogInput", ai.object_instance))
    obj = app.get_object_id(oid)
    faults.apply(obj, FaultType.freeze)
    engine.tick(2.5)
    held = float(obj.presentValue)
    engine.tick(7.5)
    assert float(obj.presentValue) == held  # frozen: no update


def test_rest_objects_and_write(served):
    app, cfg, faults, ai = served
    client = TestClient(create_app(app, cfg, faults))
    assert client.get("/devices").json()[0]["device_id"] == 1001
    objs = client.get("/objects").json()
    assert len(objs) == 8
    # write to writable PT006 (analogValue)
    r = client.post("/objects/PT006/write", json={"value": 22.0})
    assert r.status_code == 200
    assert r.json()["present_value"] == 22.0
    # non-writable PT001 rejected
    assert client.post("/objects/PT001/write", json={"value": 1.0}).status_code == 409


def test_rest_scenario_injects_fault(served):
    app, cfg, faults, ai = served
    client = TestClient(create_app(app, cfg, faults))
    r = client.post("/simulation/scenario", json={"point_id": "PT001", "fault": "out_of_service"})
    assert r.status_code == 200
    assert r.json()["out_of_service"] is True
    # unknown fault rejected
    bad = client.post("/simulation/scenario", json={"point_id": "PT001", "fault": "nope"})
    assert bad.status_code == 400
