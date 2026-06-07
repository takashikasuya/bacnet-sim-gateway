"""EP-008.1 — BACnet acquisition over loopback (PR-F-100, AC-17)."""

from __future__ import annotations

import asyncio

import pytest

from bbc_sim.bows.acquire import acquire
from bbc_sim.models import BacnetObjectType
from bbc_sim.services.client import build_client
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list


@pytest.fixture
async def server_and_client(sample_pointlist, free_port):
    cfg, _ = generate_config(
        read_point_list(sample_pointlist), bbc_id="bbc-local-001", device_id=1001
    )
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    server = build_application(cfg)
    client = build_client(f"127.0.0.1:{free_port()}")
    target = f"127.0.0.1:{cfg.network.port}"
    await asyncio.sleep(0.3)
    try:
        yield client, target
    finally:
        client.close()
        server.close()


async def test_acquire_discovers_device_and_reads_all_points(server_and_client):
    client, target = server_and_client
    device_instance, readings = await acquire(client, target)
    assert device_instance == 1001
    assert len(readings) == 8  # all 8 fixture objects, device/network-port excluded
    by_inst = {(r.object_type, r.instance) for r in readings}
    assert (BacnetObjectType.analogInput, 1001) in by_inst  # PT001
    assert (BacnetObjectType.analogValue, 1002) in by_inst  # PT006


async def test_acquire_present_values_are_present(server_and_client):
    client, target = server_and_client
    _dev, readings = await acquire(client, target)
    ai = next(
        r for r in readings if r.object_type is BacnetObjectType.analogInput and r.instance == 1001
    )
    assert ai.present_value is not None
