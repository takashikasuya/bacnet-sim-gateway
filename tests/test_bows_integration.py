"""EP-008.6 integration — BOWS → real Mosquitto, schema-validated (skipped by default).

Run with a broker:  uv run pytest -m integration
(e.g. `docker run -p 1883:1883 eclipse-mosquitto`)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import jsonschema
import pytest

from bbc_sim.bows.models import BowsConfig
from bbc_sim.bows.runner import BowsRunner
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.southbound.mqtt import MqttTransport
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list

pytestmark = pytest.mark.integration

SCHEMA = json.loads(
    (Path(__file__).parent / "fixtures" / "buildingos-bacnet-device-message.schema.json").read_text(
        encoding="utf-8"
    )
)


async def test_bows_publishes_to_mosquitto(sample_pointlist, free_port):
    cfg, _ = generate_config(
        read_point_list(sample_pointlist), bbc_id="bbc-local-001", device_id=1001
    )
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    server = build_application(cfg)
    topic = "telemetry/default/bbc-local-001"

    # subscriber on the same broker captures what BOWS publishes
    captured: list[bytes] = []

    async def _capture(_channel: str, payload: bytes) -> None:
        captured.append(payload)

    # Connect first, then subscribe — paho drops subscriptions issued before the
    # connection is established (mirrors SouthboundManager.start()).
    sub = MqttTransport("127.0.0.1", 1883)
    await sub.start()
    await asyncio.sleep(0.2)  # allow CONNACK before subscribing
    sub.subscribe(topic, _capture)
    await asyncio.sleep(0.2)  # allow SUBACK before BOWS publishes

    bows = BowsRunner(
        BowsConfig(
            target=f"127.0.0.1:{cfg.network.port}",
            device_id="bbc-local-001",
            transport_uri="mqtt://127.0.0.1:1883",
        ),
    )
    await bows.start()
    await asyncio.sleep(0.3)
    try:
        await bows.poll_once()
        await asyncio.sleep(0.5)
        assert captured, "no message received from broker"
        jsonschema.validate(json.loads(captured[-1]), SCHEMA)
    finally:
        await bows.stop()
        await sub.stop()
        server.close()
