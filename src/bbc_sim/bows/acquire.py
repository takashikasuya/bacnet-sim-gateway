"""BACnet acquisition for BOWS (PR-F-100, spec §2).

Acts as a BACnet *client* of the virtual B-BC: discover (Who-Is), enumerate the
object-list, and read present-value per object. Reuses ``services.client`` primitives.
"""

from __future__ import annotations

import logging

from bbc_sim.bows.models import Reading
from bbc_sim.models import BacnetObjectType
from bbc_sim.services.client import list_objects, read_property, whois

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

    readings: list[Reading] = []
    for ident in await list_objects(client, target):
        type_str, _, inst = ident.partition(",")
        object_type = _DASH_TO_TYPE.get(type_str)
        if object_type is None:
            continue  # device / network-port / unsupported
        try:
            value = await read_property(client, target, ident, "present-value")
        except Exception:  # noqa: BLE001 - skip unreadable object, keep the run going
            _log.warning("BOWS acquire: could not read present-value of %s", ident)
            continue
        readings.append(Reading(object_type, int(inst), value))
    return device_instance, readings
