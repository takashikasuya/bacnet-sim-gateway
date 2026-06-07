"""Wire southbound bindings to the Core Object Model (southbound-binding.md §1.1).

Telemetry: subscribe a channel, normalize, write presentValue. Command: on a northbound
WriteProperty to a command-bound object, publish the mapped value southbound.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bbc_sim.bacnet_objects.builder import oid_key, spec_to_oid
from bbc_sim.models import BacnetObjectSpec, BindingDirection, SimulatorConfig
from bbc_sim.southbound.address import derive_address, mqtt_topics
from bbc_sim.southbound.mapping import present_value_to_command, telemetry_to_present_value
from bbc_sim.southbound.transport import Transport

if TYPE_CHECKING:
    from bbc_sim.simulator_runtime.app import BBCApplication

_log = logging.getLogger(__name__)


@dataclass
class TelemetryRecord:
    ts: float
    value: Any
    quality: str  # "good" | "bad"


def channels(spec: BacnetObjectSpec) -> tuple[str, str]:
    """Return (telemetry_channel, command_channel) for an object's binding."""
    if spec.binding and spec.binding.protocol == "mqtt":
        return mqtt_topics(spec)
    base = derive_address(spec)
    return f"{base}/telemetry", f"{base}/command"


class SouthboundManager:
    """Manage southbound bindings for a running B-BC."""

    def __init__(self, app: BBCApplication, config: SimulatorConfig, transport: Transport):
        self.app = app
        self.config = config
        self.transport = transport
        self._command_channel: dict[tuple[str, int], tuple[BacnetObjectSpec, str]] = {}
        self._last_telemetry: dict[str, TelemetryRecord] = {}

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
                self._command_channel[oid_key(spec)] = (spec, cmd)

        # Register the command hook + command-bound set on the application.
        self.app.set_command_hook(self._on_command)
        self.app.set_command_oids(frozenset(self._command_channel))

    async def stop(self) -> None:
        await self.transport.stop()

    def status(self) -> dict[str, Any]:
        """Return per-protocol connection state and per-point last telemetry."""
        # Default to False: a transport with no _started attribute is reported as
        # disconnected until start() is observed, rather than falsely "connected".
        connected = getattr(self.transport, "_started", False)
        protocols: list[dict[str, Any]] = []
        seen: set[str] = set()
        for spec in self.config.objects:
            if spec.binding and spec.binding.protocol not in seen:
                seen.add(spec.binding.protocol)
                protocols.append({"protocol": spec.binding.protocol, "connected": connected})
        points: list[dict[str, Any]] = []
        for spec in self.config.objects:
            if not spec.binding:
                continue
            tele, cmd = channels(spec)
            rec = self._last_telemetry.get(spec.point_id)
            points.append(
                {
                    "point_id": spec.point_id,
                    "protocol": spec.binding.protocol,
                    "direction": spec.binding.direction.value,
                    "address": spec.binding.address or tele,
                    "last_update_ts": rec.ts if rec else None,
                    "quality": rec.quality if rec else "unknown",
                }
            )
        return {"active": True, "protocols": protocols, "points": points}

    def _telemetry_handler(self, spec: BacnetObjectSpec):
        oid = spec_to_oid(spec)

        def _mark_bad() -> None:
            self._last_telemetry[spec.point_id] = TelemetryRecord(
                ts=time.time(), value=None, quality="bad"
            )

        async def handler(_channel: str, payload: bytes) -> None:
            try:
                value = telemetry_to_present_value(spec, payload)
                obj = self.app.get_object_id(oid)
                if obj is not None:
                    obj.presentValue = value
                self._last_telemetry[spec.point_id] = TelemetryRecord(
                    ts=time.time(), value=value, quality="good"
                )
            except (ValueError, TypeError, KeyError) as exc:
                # Expected "bad payload": decode / value-conversion failures
                # (json.JSONDecodeError is a ValueError subclass) — EP-009.4.
                _log.warning("bad telemetry payload for %s: %s", spec.point_id, exc)
                _mark_bad()
            except Exception:  # noqa: BLE001 - unexpected; never kill the loop (ADR-010)
                _log.exception("unexpected telemetry handler error for %s", spec.point_id)
                _mark_bad()

        return handler

    async def _on_command(self, key: tuple[str, int], present_value: Any) -> None:
        entry = self._command_channel.get(key)
        if not entry:
            return
        spec, channel = entry
        await self.transport.publish(channel, present_value_to_command(spec, present_value))
