"""Encode BACnet readings into the Building OS `bacnet-device-message` schema.

Source of truth: `gutp-building-os-oss`
`DotNet/BuildingOS.Shared/Defines/Schemas/bacnet-device-message.json` (see
docs/specs/northbound-bows-buildingos.md §3). Pure function — snapshot-testable.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from bbc_sim.bows.models import Reading
from bbc_sim.models import BacnetObjectType

_log = logging.getLogger(__name__)

# BacnetObjectType -> (_base name, ASHRAE 135 ObjectType enum)
_OBJECT_TYPE_INFO: dict[BacnetObjectType, tuple[str, int]] = {
    BacnetObjectType.analogInput: ("AnalogInput", 0),
    BacnetObjectType.analogOutput: ("AnalogOutput", 1),
    BacnetObjectType.analogValue: ("AnalogValue", 2),
    BacnetObjectType.binaryInput: ("BinaryInput", 3),
    BacnetObjectType.binaryOutput: ("BinaryOutput", 4),
    BacnetObjectType.binaryValue: ("BinaryValue", 5),
    BacnetObjectType.multiStateInput: ("MultiStateInput", 13),
    BacnetObjectType.multiStateOutput: ("MultiStateOutput", 14),
    BacnetObjectType.multiStateValue: ("MultiStateValue", 19),
}

# ASHRAE 135 object-type enum -> BacnetObjectType. Reverse of _OBJECT_TYPE_INFO; the
# canonical mapping for decoding down-link ControlCommands (ADR-017).
ASHRAE_ENUM_TO_TYPE: dict[int, BacnetObjectType] = {
    enum: obj_type for obj_type, (_base, enum) in _OBJECT_TYPE_INFO.items()
}

_BINARY_TRUTHY = {"active", "1", "true", "on"}


def _present_value(object_type: BacnetObjectType, value: Any) -> float | int:
    """Coerce a BACnet present-value to a JSON number (schema: PresentValue=number)."""
    if object_type.is_binary:
        normalized = str(value).strip().lower()
        if normalized not in _BINARY_TRUTHY and normalized not in ("inactive", "0", "false", "off"):
            _log.debug("binary present-value %r unrecognized; encoding as 0", value)
        return 1 if normalized in _BINARY_TRUTHY else 0
    if object_type.is_multistate:
        return int(value)
    return float(value)


def _entry(reading: Reading, bacnet_device: int, now: datetime) -> dict[str, Any]:
    base, enum = _OBJECT_TYPE_INFO[reading.object_type]
    ts = reading.timestamp or now
    return {
        "TimeStamp": ts.isoformat(),
        "BACnetDevice": bacnet_device,
        "BACnetObject": {
            "_base": base,
            "_value": {"ObjectType": enum, "InstanceNo": reading.instance},
        },
        "Properties": {"PresentValue": _present_value(reading.object_type, reading.present_value)},
    }


def encode_device_message(
    device_id: str,
    bacnet_device: int,
    readings: list[Reading],
    *,
    now: datetime,
) -> list[dict[str, Any]]:
    """Encode readings for one device into a `bacnet-device-message` array (1 element)."""
    return [
        {
            "Device_id": device_id,
            "ValueString": [_entry(r, bacnet_device, now) for r in readings],
        }
    ]
