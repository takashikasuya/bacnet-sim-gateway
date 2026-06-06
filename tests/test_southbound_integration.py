"""EP-002 integration — real MQTT broker (skipped by default).

Run with a broker available:  uv run pytest -m integration
(e.g. `docker run -p 1883:1883 eclipse-mosquitto`)
"""

from __future__ import annotations

import asyncio
import json

import pytest
from bacpypes3.primitivedata import ObjectIdentifier

from bbc_sim.models import BindingDirection, BindingSpec
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.southbound.binding import SouthboundManager, channels
from bbc_sim.southbound.mqtt import MqttTransport
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list

pytestmark = pytest.mark.integration


async def test_mqtt_telemetry_updates_present_value(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    ai = next(o for o in cfg.objects if o.point_id == "PT001")
    ai.binding = BindingSpec(protocol="mqtt", direction=BindingDirection.telemetry)

    app = build_application(cfg)
    manager = SouthboundManager(app, cfg, MqttTransport("127.0.0.1", 1883))
    await manager.start()
    await asyncio.sleep(0.3)
    try:
        tele, _ = channels(ai)
        # publish via a second client through the same broker
        publisher = MqttTransport("127.0.0.1", 1883)
        await publisher.start()
        await publisher.publish(tele, json.dumps({"value": 19.0}).encode())
        await asyncio.sleep(0.5)
        obj = app.get_object_id(ObjectIdentifier(("analogInput", ai.object_instance)))
        assert float(obj.presentValue) == pytest.approx(19.0)
        await publisher.stop()
    finally:
        await manager.stop()
        app.close()
