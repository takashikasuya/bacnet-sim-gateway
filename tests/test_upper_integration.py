"""EP-004 — upper-system integration: BBMD/FDR, northbound consumer, control loop.

(AC-7/8/9/10, PR-F-041/088/089, TS-09/10)

These use loopback BACnet + the in-memory transport, so they run in the default CI
``test`` job (no broker needed). The separate ``integration`` CI job (Mosquitto) covers
the real-broker MQTT path in ``test_southbound_integration.py``.
"""

from __future__ import annotations

import asyncio

import pytest

from bbc_sim.bacnet_objects.builder import build_network_port
from bbc_sim.models import BindingDirection, BindingSpec, NetworkConfig, RuntimeMode
from bbc_sim.services.client import build_client, list_objects, read_property, write_property
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list
from bbc_sim.yaml_generator.yaml_io import config_to_dict, dict_to_config

# ---- BBMD / Foreign Device Registration (PR-F-041, AC-10) ----


def test_foreign_device_network_port():
    net = NetworkConfig(bind_address="127.0.0.1", port=0, foreign_bbmd="192.168.1.10:47808")
    np = build_network_port(net)
    assert str(np.bacnetIPMode) == "foreign"
    assert np.fdSubscriptionLifetime == 30


def test_bbmd_network_port_with_bdt():
    net = NetworkConfig(bind_address="127.0.0.1", port=0,
                        bbmd_bdt=["192.168.1.20:47808", "192.168.1.21:47808"])
    np = build_network_port(net)
    assert str(np.bacnetIPMode) == "bbmd"
    assert len(np.bbmdBroadcastDistributionTable) == 2


def test_network_bbmd_roundtrips(sample_pointlist):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1)
    cfg.network.foreign_bbmd = "10.0.0.1:47808"
    cfg.network.foreign_ttl = 60
    loaded = dict_to_config(config_to_dict(cfg))
    assert loaded.network.foreign_bbmd == "10.0.0.1:47808"
    assert loaded.network.foreign_ttl == 60

    cfg2, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1)
    cfg2.network.bbmd_bdt = ["10.0.0.2:47808", "10.0.0.3:47808"]
    loaded2 = dict_to_config(config_to_dict(cfg2))
    assert loaded2.network.bbmd_bdt == ["10.0.0.2:47808", "10.0.0.3:47808"]


# ---- Northbound consumer (Hono-style connector) over loopback (AC-7) ----


@pytest.fixture
async def gateway_runtime(sample_pointlist, free_port):
    from bbc_sim.simulator_runtime.runtime import Runtime

    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.mode = RuntimeMode.gateway
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    # command-bound writable AV for the control loop
    av = next(o for o in cfg.objects if o.point_id == "PT006")
    av.binding = BindingSpec(protocol="mqtt", direction=BindingDirection.command)
    runtime = Runtime(cfg, transport_uri="memory")
    await runtime.start()
    await asyncio.sleep(0.3)
    try:
        yield runtime, cfg, av
    finally:
        await runtime.stop()


async def test_northbound_consumer_can_enumerate_and_read(gateway_runtime, free_port):
    runtime, cfg, _av = gateway_runtime
    target = f"127.0.0.1:{cfg.network.port}"
    consumer = build_client(f"127.0.0.1:{free_port()}")  # acts like a Hono BACnet connector
    try:
        objs = await list_objects(consumer, target)
        points = [o for o in objs if "device" not in o and "network-port" not in o]
        assert len(points) == 8
        name = await read_property(consumer, target, "analog-input,1001", "object-name")
        assert name == "Supply Air Temperature"
    finally:
        consumer.close()


async def test_control_loop_north_write_to_south(gateway_runtime, free_port):  # AC-9 / TS-09
    runtime, cfg, av = gateway_runtime
    target = f"127.0.0.1:{cfg.network.port}"
    app_client = build_client(f"127.0.0.1:{free_port()}")
    try:
        await write_property(app_client, target, f"analog-value,{av.object_instance}", 26.0)
        await asyncio.sleep(0.1)
    finally:
        app_client.close()
    published = runtime.manager.transport.published
    assert any(ch.endswith("/command") for ch, _payload in published)
