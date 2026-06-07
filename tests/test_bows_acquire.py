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


# ---- hybrid RPM / per-object read (fake client, no sockets) ----


class _FakeIAm:
    def __init__(self, inst: int) -> None:
        self.iAmDeviceIdentifier = ("device", inst)
        self.pduSource = "127.0.0.1"


class _FakeClient:
    """Minimal BACnet client: object-list of 2 points (+ device/network-port)."""

    def __init__(self, *, rpm_works: bool) -> None:
        self._rpm_works = rpm_works
        self.per_object_reads = 0
        self.rpm_calls = 0

    async def who_is(self, *_a, **_k):
        return [_FakeIAm(1001)]

    async def read_property(self, _target, objid, prop):
        if objid == "device,1001" and prop == "object-list":
            return [
                ("analog-input", 1001),
                ("analog-value", 1002),
                ("device", 1001),
                ("network-port", 1),
            ]
        self.per_object_reads += 1
        return 42.0

    async def read_property_multiple(self, _address, args):
        self.rpm_calls += 1
        if not self._rpm_works:
            raise RuntimeError("RPM unsupported by device")
        # args = [objid, [props], objid2, [props2], ...] → one result row per object
        return [(args[i], "present-value", None, 7.0) for i in range(0, len(args), 2)]


async def test_acquire_uses_rpm_when_available():
    client = _FakeClient(rpm_works=True)
    dev, readings = await acquire(client, "127.0.0.1")
    assert dev == 1001
    assert {(r.object_type, r.instance) for r in readings} == {
        (BacnetObjectType.analogInput, 1001),
        (BacnetObjectType.analogValue, 1002),
    }
    assert client.rpm_calls == 1
    assert client.per_object_reads == 0  # RPM covered all points; no fallback reads
    assert all(r.present_value == 7.0 for r in readings)


async def test_acquire_falls_back_to_per_object_when_rpm_fails():
    client = _FakeClient(rpm_works=False)
    dev, readings = await acquire(client, "127.0.0.1")
    assert dev == 1001
    assert len(readings) == 2  # still acquired both points
    assert client.rpm_calls == 1  # RPM attempted
    assert client.per_object_reads == 2  # then fell back per object
    assert all(r.present_value == 42.0 for r in readings)
