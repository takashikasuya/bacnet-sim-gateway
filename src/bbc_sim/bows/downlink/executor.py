"""Execute a ControlCommand as a BACnet WriteProperty (gRPC-free, ADR-017, #74).

The executor resolves point_id -> (object_type, instance) via the shared PointRegistry
(the GW-side shared point list). Failures (unknown point_id, read-only object, transport
error) are reported as ControlResult(success=False) rather than raised.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from bbc_sim.bows.downlink.models import ControlCommand, ControlResult
from bbc_sim.bows.point_registry import PointRegistry
from bbc_sim.models import BacnetObjectType
from bbc_sim.services.client import write_property

_log = logging.getLogger(__name__)

_READ_ONLY_INPUT_TYPES = frozenset(
    {
        BacnetObjectType.analogInput,
        BacnetObjectType.binaryInput,
        BacnetObjectType.multiStateInput,
    }
)


def coerce_present_value(object_type: BacnetObjectType, value: float) -> float | int:
    """Coerce a numeric command value to the BACnet present-value form for the type."""
    if object_type.is_binary:
        return 1 if float(value) >= 0.5 else 0
    if object_type.is_multistate:
        return int(round(float(value)))
    return float(value)


def _valid_priority(priority: int | None) -> int | None:
    return priority if priority is not None and 1 <= priority <= 16 else None


class CommandExecutor:
    """Turn ControlCommands into WriteProperty calls against one target B-BC.

    Resolves point_id -> (object_type, instance) via the shared PointRegistry.
    Commands for unknown point_ids are rejected without a BACnet write.
    """

    def __init__(self, app: Any, target: str, *, point_registry: PointRegistry) -> None:
        self._app = app
        self._target = target
        self._registry = point_registry

    async def execute(self, cmd: ControlCommand) -> ControlResult:
        resolved = self._registry.resolve_point_id(cmd.point_id)
        if resolved is None:
            return ControlResult(cmd.control_id, False, f"unknown point_id {cmd.point_id!r}")
        object_type, instance_no = resolved
        if object_type in _READ_ONLY_INPUT_TYPES:
            return ControlResult(
                cmd.control_id,
                False,
                f"{object_type.value} is read-only (Input); not writable",
            )
        objid = f"{object_type.value},{instance_no}"
        value = coerce_present_value(object_type, cmd.present_value)
        priority = _valid_priority(cmd.priority)
        try:
            await write_property(self._app, self._target, objid, value, priority=priority)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            _log.warning("down-link WriteProperty %s=%r failed: %s", objid, value, exc)
            return ControlResult(cmd.control_id, False, f"{type(exc).__name__}: {exc}")
        return ControlResult(cmd.control_id, True, "ok")
