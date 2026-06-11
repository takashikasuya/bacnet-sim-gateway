"""Execute a ControlCommand as a BACnet WriteProperty (gRPC-free, ADR-017).

The connector writes present-value to the target B-BC as a northbound BACnet client
(ADR-014); the B-BC's own north=BACnet / south=binding directions are unchanged
(ADR-005). Failures (unknown type, writeAccessDenied, transport error) are reported as
``ControlResult(success=False)`` rather than raised, so one bad command never tears down
the stream.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from bbc_sim.bows.downlink.models import ControlCommand, ControlResult
from bbc_sim.bows.encoder import ASHRAE_ENUM_TO_TYPE
from bbc_sim.models import BacnetObjectType
from bbc_sim.services.client import write_property

_log = logging.getLogger(__name__)

# Input objects (AI/BI/MI) are sensor reads, not commandable; down-link control targets
# writable Output/Value objects (ADR-017 "writable objects only"). Reject Input writes up
# front with a clean ControlResult rather than relying on a BACnet writeAccessDenied.
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
        # State numbers arrive as whole doubles (1.0, 2.0); round() is half-to-even, which
        # only matters on exact .5 boundaries that Building OS is not expected to send.
        return int(round(float(value)))
    return float(value)


def _valid_priority(priority: int | None) -> int | None:
    return priority if priority is not None and 1 <= priority <= 16 else None


class CommandExecutor:
    """Turn ControlCommands into WriteProperty calls against one target B-BC.

    One egress stream fronts a single target B-BC (``target``). When ``expected_device``
    is set, commands whose ``bacnet_device`` differs are rejected (fail-as-result) so a
    misrouted command never writes to the wrong device; when None, the device id is not
    enforced (single-target, best-effort).
    """

    def __init__(self, app: Any, target: str, *, expected_device: int | None = None) -> None:
        self._app = app
        self._target = target
        self._expected_device = expected_device

    async def execute(self, cmd: ControlCommand) -> ControlResult:
        if self._expected_device is not None and cmd.bacnet_device != self._expected_device:
            return ControlResult(
                cmd.control_id,
                False,
                f"command targets device {cmd.bacnet_device}; "
                f"this connector serves device {self._expected_device}",
            )
        object_type = ASHRAE_ENUM_TO_TYPE.get(cmd.object_type)
        if object_type is None:
            return ControlResult(cmd.control_id, False, f"unknown object_type {cmd.object_type}")
        if object_type in _READ_ONLY_INPUT_TYPES:
            return ControlResult(
                cmd.control_id, False, f"{object_type.value} is read-only (Input); not writable"
            )
        objid = f"{object_type.value},{cmd.instance_no}"
        value = coerce_present_value(object_type, cmd.present_value)
        priority = _valid_priority(cmd.priority)
        try:
            await write_property(self._app, self._target, objid, value, priority=priority)
        except asyncio.CancelledError:
            raise  # never turn shutdown/cancellation into a ControlResult failure
        except Exception as exc:  # noqa: BLE001 - report failure, keep the stream alive
            _log.warning("down-link WriteProperty %s=%r failed: %s", objid, value, exc)
            return ControlResult(cmd.control_id, False, f"{type(exc).__name__}: {exc}")
        return ControlResult(cmd.control_id, True, "ok")
