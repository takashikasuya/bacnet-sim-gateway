"""MQTT southbound transport (paho-mqtt). Real network I/O; tests are integration.

Bridges paho's threaded callbacks onto the asyncio loop so the Core Object Model stays
event-loop-confined (ADR-010): inbound messages are scheduled with
``run_coroutine_threadsafe``.
"""

from __future__ import annotations

import asyncio

import paho.mqtt.client as mqtt

from bbc_sim.southbound.transport import Handler


class MqttTransport:
    """Transport backed by an MQTT broker."""

    def __init__(self, host: str = "127.0.0.1", port: int = 1883) -> None:
        self.host = host
        self.port = port
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._handlers: dict[str, list[Handler]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._client.on_message = self._on_message

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._client.connect(self.host, self.port)
        self._client.loop_start()

    async def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def subscribe(self, channel: str, handler: Handler) -> None:
        self._handlers.setdefault(channel, []).append(handler)
        self._client.subscribe(channel)

    async def publish(self, channel: str, payload: bytes) -> None:
        self._client.publish(channel, payload)

    def _on_message(self, _client, _userdata, msg: mqtt.MQTTMessage) -> None:
        if self._loop is None:
            return
        topic, payload = msg.topic, bytes(msg.payload)
        for handler in self._handlers.get(topic, []):

            async def _dispatch(h: Handler = handler) -> None:
                await h(topic, payload)

            asyncio.run_coroutine_threadsafe(_dispatch(), self._loop)
