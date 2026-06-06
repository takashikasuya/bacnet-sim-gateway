"""Wire southbound bindings to the Core Object Model (southbound-binding.md §1.1).

Telemetry: subscribe a channel, normalize, write presentValue. Command: on a northbound
WriteProperty to a command-bound object, publish the mapped value southbound.
"""

from __future__ import annotations

import logging
from typing import Any

from bacpypes3.app import Application
from bacpypes3.primitivedata import ObjectIdentifier

from bbc_sim.bacnet_objects.builder import _OID_TYPE
from bbc_sim.models import BacnetObjectSpec, BindingDirection, SimulatorConfig
from bbc_sim.southbound.address import derive_address, mqtt_topics
from bbc_sim.southbound.mapping import present_value_to_command, telemetry_to_present_value
from bbc_sim.southbound.transport import Transport

_log = logging.getLogger(__name__)


def _oid_key(spec: BacnetObjectSpec) -> tuple[str, int]:
    """Match the (dash-type, instance) key used by BBCApplication."""
    return (str(ObjectIdentifier((_OID_TYPE[spec.object_type], spec.object_instance))[0]),
            spec.object_instance)


def channels(spec: BacnetObjectSpec) -> tuple[str, str]:
    """Return (telemetry_channel, command_channel) for an object's binding."""
    if spec.binding and spec.binding.protocol == "mqtt":
        return mqtt_topics(spec)
    base = derive_address(spec)
    return f"{base}/telemetry", f"{base}/command"


class SouthboundManager:
    """Manage southbound bindings for a running B-BC."""

    def __init__(self, app: Application, config: SimulatorConfig, transport: Transport):
        self.app = app
        self.config = config
        self.transport = transport
        self._command_channel: dict[tuple[str, int], tuple[BacnetObjectSpec, str]] = {}

    async def start(self) -> None:
        await self.transport.start()
        for spec in self.config.objects:
            if not spec.binding:
                continue
            tele, cmd = channels(spec)
            direction = spec.binding.direction
            if direction in (BindingDirection.telemetry, BindingDirection.both):
                self.transport.subscribe(tele, self._telemetry_handler(spec))
            if direction in (BindingDirection.command, BindingDirection.both):
                self._command_channel[_oid_key(spec)] = (spec, cmd)

        # Register the command hook + command-bound set on the application.
        self.app.on_command = self._on_command  # type: ignore[attr-defined]
        self.app._command_oids = frozenset(self._command_channel)  # type: ignore[attr-defined]

    async def stop(self) -> None:
        await self.transport.stop()

    def _telemetry_handler(self, spec: BacnetObjectSpec):
        oid = ObjectIdentifier((_OID_TYPE[spec.object_type], spec.object_instance))

        async def handler(_channel: str, payload: bytes) -> None:
            try:
                value = telemetry_to_present_value(spec, payload)
                obj = self.app.get_object_id(oid)
                if obj is not None:
                    obj.presentValue = value
            except Exception:  # noqa: BLE001 - never let a bad payload kill the loop
                _log.exception("telemetry handling failed for %s", spec.point_id)

        return handler

    async def _on_command(self, oid_key: tuple[str, int], present_value: Any) -> None:
        entry = self._command_channel.get(oid_key)
        if not entry:
            return
        spec, channel = entry
        await self.transport.publish(channel, present_value_to_command(spec, present_value))
