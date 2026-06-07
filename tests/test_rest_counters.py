"""EP-007.2 — BBCApplication counter increments (PR-F-054)."""

from __future__ import annotations

import pytest

from bbc_sim.simulator_runtime.app import Counters, build_application, compute_writable_oids
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list


@pytest.fixture
def app_with_config(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    bapp = build_application(cfg, with_network=False)
    try:
        yield bapp, cfg
    finally:
        bapp.close()


def test_counters_initialised_to_zero(app_with_config):
    bapp, _ = app_with_config
    c = bapp.counters
    assert c.who_is == 0
    assert c.i_am_sent == 0
    assert c.read_property == 0
    assert c.read_property_multiple == 0
    assert c.write_property == 0
    assert c.write_property_multiple == 0
    assert c.write_access_denied == 0


def test_counters_dataclass_fields():
    c = Counters()
    assert hasattr(c, "who_is")
    assert hasattr(c, "read_property")
    assert hasattr(c, "write_access_denied")


def test_build_application_sets_counters(app_with_config):
    bapp, _ = app_with_config
    assert isinstance(bapp.counters, Counters)


def test_compute_writable_oids_reflects_config(app_with_config):
    _, cfg = app_with_config
    writable_ids = compute_writable_oids(cfg)
    writable_specs = [s for s in cfg.objects if s.writable]
    assert len(writable_ids) == len(writable_specs)


def test_write_access_denied_increments_counter_via_rest(app_with_config):
    """Non-writable write via REST increments write_access_denied on BBCApplication."""
    import asyncio
    from unittest.mock import MagicMock

    from bacpypes3.apdu import WritePropertyRequest
    from bacpypes3.errors import ExecutionError

    bapp, cfg = app_with_config
    non_writable = next(s for s in cfg.objects if not s.writable)

    from bacpypes3.primitivedata import ObjectIdentifier

    from bbc_sim.bacnet_objects.builder import _OID_TYPE
    oid = ObjectIdentifier((_OID_TYPE[non_writable.object_type], non_writable.object_instance))

    apdu = MagicMock(spec=WritePropertyRequest)
    apdu.objectIdentifier = oid
    apdu.propertyIdentifier = "present-value"

    before = bapp.counters.write_access_denied
    loop = asyncio.new_event_loop()
    try:
        with pytest.raises(ExecutionError):
            loop.run_until_complete(bapp.do_WritePropertyRequest(apdu))
    finally:
        loop.close()
    assert bapp.counters.write_access_denied == before + 1


def test_rest_write_does_not_affect_bacnet_counters(sample_pointlist, free_port):
    """REST /objects/{id}/write bypasses the BACnet stack — counters stay at zero."""
    from fastapi.testclient import TestClient

    from bbc_sim.rest.api import create_app

    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    bapp = build_application(cfg, with_network=False)
    client = TestClient(create_app(bapp, cfg))
    try:
        # PT006 is an analog-value writable point (confirmed by test_engine_rest.py)
        r = client.post("/objects/PT006/write", json={"value": 22.0})
        assert r.status_code == 200
        # REST write calls obj.presentValue directly, not the BACnet WP handler
        assert bapp.counters.write_property == 0
        assert bapp.counters.write_access_denied == 0
    finally:
        bapp.close()
