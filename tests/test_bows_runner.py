"""EP-008.3/.4/.5 — runner publish + CLI registration + identity (PR-F-102/103/104, AC-19)."""

from __future__ import annotations

import asyncio
import json

import pytest
from typer.testing import CliRunner

from bbc_sim.bows.models import BowsConfig
from bbc_sim.bows.runner import BowsRunner
from bbc_sim.cli import app
from bbc_sim.services.client import build_client  # noqa: F401 (ensures import chain ok)
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.southbound.transport import InMemoryTransport
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list

runner = CliRunner()


def test_bows_command_registered():
    out = runner.invoke(app, ["bows", "--help"]).output
    assert "run" in out
    assert runner.invoke(app, ["bows", "run", "--help"]).exit_code == 0


def test_topic_uses_tenant_and_device_id():
    cfg = BowsConfig(target="x", device_id="bbc-local-001", tenant="site-a")
    assert BowsRunner(cfg, transport=InMemoryTransport()).topic == \
        "telemetry/site-a/bbc-local-001"


@pytest.fixture
async def bbc_server(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="bbc-local-001",
                             device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    server = build_application(cfg)
    target = f"127.0.0.1:{cfg.network.port}"
    await asyncio.sleep(0.3)
    try:
        yield target
    finally:
        server.close()


async def test_poll_once_publishes_valid_message(bbc_server):
    transport = InMemoryTransport()
    cfg = BowsConfig(target=bbc_server, device_id="bbc-local-001", tenant="default")
    bows = BowsRunner(cfg, transport=transport)
    await bows.start()
    try:
        message = await bows.poll_once()
    finally:
        await bows.stop()

    # published to the right topic
    assert len(transport.published) == 1
    channel, payload = transport.published[0]
    assert channel == "telemetry/default/bbc-local-001"

    # payload conforms to bacnet-device-message shape
    decoded = json.loads(payload)
    assert decoded == message
    assert isinstance(decoded, list) and len(decoded) == 1
    dev = decoded[0]
    assert dev["Device_id"] == "bbc-local-001"
    assert len(dev["ValueString"]) == 8
    entry = dev["ValueString"][0]
    assert {"TimeStamp", "BACnetDevice", "BACnetObject", "Properties"} <= entry.keys()
    assert entry["BACnetDevice"] == 1001
    assert "ObjectType" in entry["BACnetObject"]["_value"]
    assert isinstance(entry["Properties"]["PresentValue"], (int, float))
