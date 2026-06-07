"""BACnet acquisition for BOWS (PR-F-100, spec §2).

Acts as a BACnet *client* of the virtual B-BC: discover (Who-Is), enumerate the
object-list, and read present-value per object. Reuses ``services.client`` primitives.
"""

from __future__ import annotations

import logging

from bbc_sim.bows.models import Reading
from bbc_sim.models import BacnetObjectType
from bbc_sim.services.client import read_present_values, read_property, whois

_log = logging.getLogger(__name__)

# dash-form object-type token (as rendered by bacpypes3) -> BacnetObjectType
_DASH_TO_TYPE: dict[str, BacnetObjectType] = {
    "analog-input": BacnetObjectType.analogInput,
    "analog-output": BacnetObjectType.analogOutput,
    "analog-value": BacnetObjectType.analogValue,
    "binary-input": BacnetObjectType.binaryInput,
    "binary-output": BacnetObjectType.binaryOutput,
    "binary-value": BacnetObjectType.binaryValue,
    "multi-state-input": BacnetObjectType.multiStateInput,
    "multi-state-output": BacnetObjectType.multiStateOutput,
    "multi-state-value": BacnetObjectType.multiStateValue,
}


async def acquire(client, target: str) -> tuple[int, list[Reading]]:
    """Return (device_instance, readings) for the B-BC at ``target``.

    Non-point objects (device, network-port, unknown types) are skipped. Objects whose
    present-value cannot be read are skipped with a warning rather than aborting the run.
    """
    found = await whois(client, target)
    if not found:
        _log.warning("BOWS acquire: no device found at %s", target)
        return 0, []
    device_instance = found[0][0]

    # Read the object-list directly from the discovered device (avoids a second Who-Is).
    object_list = await read_property(client, target, f"device,{device_instance}", "object-list")

    # Recognized point objects (device/network-port/unsupported are skipped).
    points: list[tuple[str, BacnetObjectType, int]] = []
    for obj in object_list:
        ident = f"{obj[0]},{obj[1]}"
        type_str, _, inst_str = ident.partition(",")
        object_type = _DASH_TO_TYPE.get(type_str)
        if object_type is None:
            continue
        points.append((ident, object_type, int(inst_str)))

    # Hybrid read (spec §2 / Issue #42): one ReadPropertyMultiple for all present-values,
    # then a per-object ReadProperty fallback for any the device didn't return (or if the
    # whole RPM fails). This keeps the round-trip savings while staying resilient to a
    # single unreadable point.
    batched: dict[str, object] = {}
    try:
        batched = await read_present_values(client, target, [p[0] for p in points])
    except Exception as exc:  # noqa: BLE001 - fall back to per-object reads
        _log.warning("BOWS acquire: RPM batch failed (%s); using per-object reads", exc)

    readings: list[Reading] = []
    for ident, object_type, inst in points:
        if ident in batched:
            value = batched[ident]
        else:
            try:
                value = await read_property(client, target, ident, "present-value")
            except Exception as exc:  # noqa: BLE001 - skip unreadable object, keep going
                _log.warning("BOWS acquire: could not read present-value of %s: %s", ident, exc)
                continue
        readings.append(Reading(object_type, inst, value))
    return device_instance, readings
