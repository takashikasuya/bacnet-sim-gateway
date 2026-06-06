"""EP-003.3/.4 — COV and WritePropertyMultiple over loopback (PR-F-028, PR-F-025)."""

from __future__ import annotations

import asyncio

import pytest
from bacpypes3.apdu import (
    PropertyValue,
    WriteAccessSpecification,
    WritePropertyMultipleError,
    WritePropertyMultipleRequest,
)
from bacpypes3.constructeddata import Any as BAny
from bacpypes3.primitivedata import ObjectIdentifier, Real

from bbc_sim.services.client import (
    build_client,
    capture_cov_notifications,
    read_property,
    subscribe_cov,
    write_property_multiple,
)
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list


@pytest.fixture
async def server_and_client(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    server = build_application(cfg)
    client = build_client(f"127.0.0.1:{free_port()}")
    target = f"127.0.0.1:{cfg.network.port}"
    await asyncio.sleep(0.3)
    try:
        yield server, client, target
    finally:
        client.close()
        server.close()


async def test_write_property_multiple_writable(server_and_client):  # PR-F-025
    server, client, target = server_and_client
    await write_property_multiple(client, target, [("analog-value,1002", 31.0)])
    pv = await read_property(client, target, "analog-value,1002", "present-value")
    assert float(pv) == 31.0


async def test_write_property_multiple_rejects_input(sample_pointlist):  # AC-5
    # Unit-level: the handler must raise WritePropertyMultipleError(writeAccessDenied)
    # for a present-value write to a non-writable Input. (bacpypes3 0.0.106 cannot
    # transport WPM error responses over IP, so this is verified server-side.)
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    app = build_application(cfg, with_network=False)
    req = WritePropertyMultipleRequest(
        listOfWriteAccessSpecs=[
            WriteAccessSpecification(
                objectIdentifier=ObjectIdentifier("analog-input,1001"),
                listOfProperties=[
                    PropertyValue(propertyIdentifier="present-value", value=BAny(Real(5.0)))
                ],
            )
        ]
    )
    with pytest.raises(WritePropertyMultipleError):
        await app.do_WritePropertyMultipleRequest(req)


async def test_cov_notification_on_change(server_and_client):  # PR-F-028
    server, client, target = server_and_client
    captured = capture_cov_notifications(client)
    await subscribe_cov(client, target, "analog-value,1002", confirmed=False)
    await asyncio.sleep(0.3)
    obj = server.get_object_id(ObjectIdentifier("analog-value,1002"))
    obj.presentValue = 48.0
    await asyncio.sleep(0.6)
    assert any("analog-value" in oid for _kind, oid in captured)
