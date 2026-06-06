"""Value transforms between southbound payloads and BACnet presentValue.

Telemetry: payload -> normalized presentValue (scale/offset, type, enum_map).
Command: presentValue -> payload. Payloads are JSON bytes with a ``value`` field
(or the raw scalar). Keeps simulator and gateway logically consistent (PR-NF-017).
"""

from __future__ import annotations

import json
from typing import Any

from bbc_sim.models import BacnetObjectSpec, BindingMapping


def _extract(payload: bytes) -> Any:
    """Decode a payload to a scalar. Accepts JSON {"value": x}, JSON scalar, or text."""
    text = payload.decode("utf-8").strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(obj, dict):
        return obj.get("value")
    return obj


def telemetry_to_present_value(spec: BacnetObjectSpec, payload: bytes) -> Any:
    """Convert an inbound telemetry payload to a BACnet presentValue."""
    m: BindingMapping = spec.binding.mapping if spec.binding else BindingMapping()
    raw = _extract(payload)
    if spec.object_type.is_analog or m.type == "real":
        return float(raw) * m.scale + m.offset
    if spec.object_type.is_binary or m.type == "boolean":
        truthy = str(raw).lower() in ("1", "true", "on", "active", "yes")
        return "active" if truthy else "inactive"
    # multi-state / unsigned / enum
    if m.enum_map:
        # enum_map maps index -> label; accept either index or label
        for idx, label in m.enum_map.items():
            if str(raw) == idx or str(raw) == label:
                return int(idx)
    return int(float(raw))


def present_value_to_command(spec: BacnetObjectSpec, present_value: Any) -> bytes:
    """Convert a BACnet presentValue to an outbound command payload (JSON bytes)."""
    m: BindingMapping = spec.binding.mapping if spec.binding else BindingMapping()
    value: Any
    if spec.object_type.is_analog or m.type == "real":
        value = (float(present_value) - m.offset) / m.scale if m.scale else 0.0
    elif spec.object_type.is_binary or m.type == "boolean":
        value = str(present_value) in ("active", "True", "1")
    else:
        value = int(present_value)
    return json.dumps({"value": value}).encode("utf-8")
