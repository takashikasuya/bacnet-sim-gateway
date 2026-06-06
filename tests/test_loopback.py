"""EP-001.6/.7 — loopback integration: Who-Is/Read/RPM/Write (TS-02..05, AC-2..5).

These exercise the real bacpypes3 BACnet/IP stack over 127.0.0.1.
"""

from __future__ import annotations

import asyncio

import pytest
from bacpypes3.apdu import ErrorRejectAbortNack

from bbc_sim.services.client import (
    build_client,
    list_objects,
    read_property,
    read_property_multiple,
    whois,
    write_property,
)
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list


@pytest.fixture
async def server_and_client(sample_pointlist, free_port):
    points = read_point_list(sample_pointlist)
    cfg, _ = generate_config(points, bbc_id="bbc-local-001", device_id=1001)
    server_port = free_port()
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = server_port

    server = build_application(cfg)
    client = build_client(f"127.0.0.1:{free_port()}")
    target = f"127.0.0.1:{server_port}"
    await asyncio.sleep(0.3)  # let datalinks come up
    try:
        yield target, client
    finally:
        client.close()
        server.close()


async def test_whois_discovers_device(server_and_client):  # TS-02 / AC-2
    target, client = server_and_client
    found = await whois(client, target)
    assert any(dev_id == 1001 for dev_id, _addr in found)


async def test_read_property(server_and_client):  # TS-03 / AC-3
    target, client = server_and_client
    name = await read_property(client, target, "analog-input,1001", "object-name")
    assert name == "Supply Air Temperature"
    units = await read_property(client, target, "analog-input,1001", "units")
    assert str(units) == "degrees-celsius"


async def test_read_property_multiple(server_and_client):  # TS-04 / AC-4
    target, client = server_and_client
    results = await read_property_multiple(
        client, target, "analog-input,1001", ["present-value", "units", "object-name"]
    )
    props = {str(prop): value for _oid, prop, _idx, value in results}
    assert "present-value" in props
    assert props["object-name"] == "Supply Air Temperature"


async def test_write_property_on_writable(server_and_client):  # TS-05 / AC-5
    target, client = server_and_client
    await write_property(client, target, "analog-value,1002", 23.5)
    pv = await read_property(client, target, "analog-value,1002", "present-value")
    assert float(pv) == 23.5


async def test_write_property_rejected_on_input(server_and_client):  # AC-5
    target, client = server_and_client
    # analog-input present-value is read-only; a write must be rejected (AC-5).
    with pytest.raises(ErrorRejectAbortNack) as exc:
        await write_property(client, target, "analog-input,1001", 99.9)
    assert "write-access-denied" in str(exc.value)


async def test_list_objects(server_and_client):
    target, client = server_and_client
    objs = await list_objects(client, target)
    assert any("analog-input" in o and o.endswith(",1001") for o in objs)
    # device + network-port + 8 points
    assert len([o for o in objs if "device" not in o and "network-port" not in o]) == 8
