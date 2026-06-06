"""EP-002 — modes + southbound binding (PR-F-080..090, ADR-005/013, TS-06/12/13)."""

from __future__ import annotations

import asyncio
import json

import pytest
from bacpypes3.primitivedata import ObjectIdentifier

from bbc_sim.models import BindingDirection, BindingMapping, BindingSpec
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.southbound.address import derive_address, mqtt_topics
from bbc_sim.southbound.binding import SouthboundManager, channels
from bbc_sim.southbound.factory import make_transport
from bbc_sim.southbound.mapping import present_value_to_command, telemetry_to_present_value
from bbc_sim.southbound.transport import InMemoryTransport
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list

# ---- address / topic derivation ----


def test_derive_address_local_id_first(sample_pointlist):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1)
    pt001 = next(o for o in cfg.objects if o.point_id == "PT001")
    assert derive_address(pt001) == "LOCAL001"  # local_id wins


def test_mqtt_topics_follow_spec(sample_pointlist):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1)
    pt001 = next(o for o in cfg.objects if o.point_id == "PT001")
    tele, cmd = mqtt_topics(pt001)
    assert tele == "building/MainBldg/device/DEV001/point/PT001/telemetry"
    assert cmd.endswith("/command")


def test_explicit_binding_address_overrides(sample_pointlist):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1)
    o = cfg.objects[0]
    o.binding = BindingSpec(protocol="mqtt", address="custom/topic")
    assert derive_address(o) == "custom/topic"


# ---- value mapping ----


def test_telemetry_analog_scale_offset(sample_pointlist):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1)
    o = next(x for x in cfg.objects if x.point_id == "PT001")
    o.binding = BindingSpec(protocol="mqtt", mapping=BindingMapping(scale=0.1, offset=5.0))
    pv = telemetry_to_present_value(o, json.dumps({"value": 100}).encode())
    assert pv == pytest.approx(15.0)


def test_command_roundtrip_value(sample_pointlist):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1)
    o = next(x for x in cfg.objects if x.point_id == "PT006")  # analogValue
    o.binding = BindingSpec(protocol="mqtt", direction=BindingDirection.command)
    payload = present_value_to_command(o, 23.5)
    assert json.loads(payload)["value"] == pytest.approx(23.5)


def test_binary_telemetry_default_mapping(sample_pointlist):
    # binary object with a default (type='real') mapping must still produce a BinaryPV.
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1)
    o = next(x for x in cfg.objects if x.point_id == "PT003")  # binaryInput
    o.binding = BindingSpec(protocol="mqtt")
    assert telemetry_to_present_value(o, json.dumps({"value": True}).encode()) == "active"
    assert telemetry_to_present_value(o, json.dumps({"value": 0}).encode()) == "inactive"


def test_binary_command_default_mapping(sample_pointlist):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1)
    o = next(x for x in cfg.objects if x.point_id == "PT004")  # binaryOutput (writable)
    o.binding = BindingSpec(protocol="mqtt", direction=BindingDirection.command)
    assert json.loads(present_value_to_command(o, "active"))["value"] is True
    assert json.loads(present_value_to_command(o, "inactive"))["value"] is False


def test_multistate_telemetry_enum_map(sample_pointlist):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1)
    o = next(x for x in cfg.objects if x.point_id == "PT007")  # multiStateValue
    o.binding = BindingSpec(
        protocol="mqtt",
        mapping=BindingMapping(type="enum", enum_map={"1": "Auto", "2": "Manual", "3": "Off"}),
    )
    assert telemetry_to_present_value(o, json.dumps({"value": "Manual"}).encode()) == 2
    assert telemetry_to_present_value(o, json.dumps({"value": 3}).encode()) == 3


# ---- binding manager over the real object model ----


@pytest.fixture
async def gateway_app(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    # PT001 (AI) telemetry-bound; PT006 (AV, writable) command-bound.
    ai = next(o for o in cfg.objects if o.point_id == "PT001")
    ai.binding = BindingSpec(protocol="mqtt", direction=BindingDirection.telemetry)
    av = next(o for o in cfg.objects if o.point_id == "PT006")
    av.binding = BindingSpec(protocol="mqtt", direction=BindingDirection.command)

    app = build_application(cfg)
    transport = InMemoryTransport()
    manager = SouthboundManager(app, cfg, transport)
    await manager.start()
    await asyncio.sleep(0.2)
    try:
        yield app, cfg, transport, ai, av
    finally:
        await manager.stop()
        app.close()


async def test_telemetry_updates_present_value(gateway_app):  # TS-06 / PR-F-082,084
    app, cfg, transport, ai, _av = gateway_app
    tele, _cmd = channels(ai)
    await transport.feed(tele, json.dumps({"value": 21.5}).encode())
    obj = app.get_object_id(ObjectIdentifier(("analogInput", ai.object_instance)))
    assert float(obj.presentValue) == pytest.approx(21.5)


async def test_command_publishes_southbound(gateway_app):  # TS-06 / PR-F-083,090
    app, cfg, transport, _ai, av = gateway_app
    obj = app.get_object_id(ObjectIdentifier(("analogValue", av.object_instance)))
    # simulate a northbound write by invoking the command hook path directly
    obj.presentValue = 42.0
    await app.on_command(("analog-value", av.object_instance), obj.presentValue)
    _tele, cmd = channels(av)
    assert any(ch == cmd for ch, _payload in transport.published)
    last = transport.published[-1][1]
    assert json.loads(last)["value"] == pytest.approx(42.0)


async def test_logical_equivalence_telemetry(gateway_app):  # AC-13 / PR-NF-017
    app, cfg, transport, ai, _av = gateway_app
    tele, _ = channels(ai)
    for val in (10.0, 0.0, 33.3):
        await transport.feed(tele, json.dumps({"value": val}).encode())
        obj = app.get_object_id(ObjectIdentifier(("analogInput", ai.object_instance)))
        assert float(obj.presentValue) == pytest.approx(val)


async def test_command_via_northbound_write(gateway_app, free_port):  # AC-9 path
    # A real northbound WriteProperty to the command-bound AV must publish southbound.
    from bbc_sim.services.client import build_client, write_property

    app, cfg, transport, _ai, av = gateway_app
    target = f"127.0.0.1:{cfg.network.port}"
    client = build_client(f"127.0.0.1:{free_port()}")
    await asyncio.sleep(0.2)
    try:
        await write_property(client, target, f"analog-value,{av.object_instance}", 27.0)
        await asyncio.sleep(0.1)
    finally:
        client.close()
    _tele, cmd = channels(av)
    assert any(ch == cmd for ch, _payload in transport.published)


# ---- transport factory ----


def test_factory_memory():
    assert isinstance(make_transport("memory"), InMemoryTransport)


def test_factory_rejects_unknown():
    with pytest.raises(ValueError):
        make_transport("carrier-pigeon://nest")


def test_command_binding_on_nonwritable_is_invalid(sample_pointlist):
    from bbc_sim.yaml_generator.yaml_io import validate_config

    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1)
    ai = next(o for o in cfg.objects if o.point_id == "PT001")  # writable=False
    ai.binding = BindingSpec(protocol="mqtt", direction=BindingDirection.command)
    errors = validate_config(cfg)
    assert any("command binding requires writable" in e for e in errors)


def test_command_scale_zero_raises(sample_pointlist):
    # scale=0 would silently emit 0.0 and mask a config error -> must raise (review #33).
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1)
    o = next(x for x in cfg.objects if x.point_id == "PT006")  # analogValue
    o.binding = BindingSpec(
        protocol="mqtt", direction=BindingDirection.command,
        mapping=BindingMapping(scale=0.0),
    )
    with pytest.raises(ValueError):
        present_value_to_command(o, 5.0)
