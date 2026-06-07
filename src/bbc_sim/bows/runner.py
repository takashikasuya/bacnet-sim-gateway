"""BOWS runner: single-loop acquire → encode → publish (ADR-010, spec §1).

Reads the virtual B-BC over BACnet and publishes Building OS `bacnet-device-message`
telemetry to `telemetry/{tenant}/{deviceId}` via the southbound Transport abstraction
(ADR-013). The connector's MQTT/AMQP output is the connector→Building OS link, not a
B-BC interface (ADR-014).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

from bbc_sim.bows.acquire import acquire
from bbc_sim.bows.encoder import encode_device_message
from bbc_sim.bows.models import BowsConfig
from bbc_sim.services.client import build_client, ephemeral_local
from bbc_sim.southbound.factory import make_transport
from bbc_sim.southbound.transport import Transport

_log = logging.getLogger(__name__)


class BowsRunner:
    """Own the BACnet client + transport for the lifetime of a BOWS run."""

    def __init__(self, config: BowsConfig, transport: Transport | None = None) -> None:
        self.config = config
        self.transport = transport or make_transport(config.transport_uri)
        self.client: Any = None

    @property
    def topic(self) -> str:
        # localId = {tenant}/{device_id}; Building OS resolves point_id server-side.
        return f"telemetry/{self.config.tenant}/{self.config.device_id}"

    async def start(self) -> None:
        self.client = build_client(self.config.local_address or ephemeral_local())
        try:
            await self.transport.start()
        except Exception:  # don't leak the BACnet client if the transport fails to start
            self.client.close()
            self.client = None
            raise

    async def stop(self) -> None:
        if self.client is not None:
            self.client.close()
        await self.transport.stop()

    async def poll_once(self) -> list[dict[str, Any]]:
        """Acquire the B-BC, encode, publish once. Returns the message sent."""
        device_instance, readings = await acquire(self.client, self.config.target)
        message = encode_device_message(
            self.config.device_id, device_instance, readings, now=datetime.now(UTC)
        )
        await self.transport.publish(self.topic, json.dumps(message).encode("utf-8"))
        return message

    async def run_forever(self, stop: asyncio.Event | None = None) -> None:
        stop = stop or asyncio.Event()
        await self.start()
        try:
            while not stop.is_set():
                try:
                    await self.poll_once()
                except Exception:  # noqa: BLE001 - keep polling despite transient errors
                    _log.exception("BOWS poll failed")
                try:
                    await asyncio.wait_for(stop.wait(), timeout=self.config.interval)
                except TimeoutError:
                    pass
        finally:
            await self.stop()


def run(config: BowsConfig) -> None:
    """Blocking entry point for the CLI."""
    asyncio.run(BowsRunner(config).run_forever())
