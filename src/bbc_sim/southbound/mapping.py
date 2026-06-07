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


def _is_truthy(raw: Any) -> bool:
    return str(raw).lower() in ("1", "true", "on", "active", "yes")


def telemetry_to_present_value(spec: BacnetObjectSpec, payload: bytes) -> Any:
    """Convert an inbound telemetry payload to a BACnet presentValue.

    The BACnet object type decides the value family; ``mapping.type`` is only a hint
    used when the object type is ambiguous.
    """
    m: BindingMapping = spec.binding.mapping if spec.binding else BindingMapping()
    raw = _extract(payload)
    if spec.object_type.is_binary or (not spec.object_type.is_analog and m.type == "boolean"):
        return "active" if _is_truthy(raw) else "inactive"
    if spec.object_type.is_multistate or m.type in ("unsigned", "enum"):
        if m.enum_map:
            # enum_map maps index -> label; accept either index or label.
            for idx, label in m.enum_map.items():
                if str(raw) == idx or str(raw) == label:
                    return int(idx)
        return int(float(raw))
    # analog / real (default)
    return float(raw) * m.scale + m.offset


def present_value_to_command(spec: BacnetObjectSpec, present_value: Any) -> bytes:
    """Convert a BACnet presentValue to an outbound command payload (JSON bytes)."""
    m: BindingMapping = spec.binding.mapping if spec.binding else BindingMapping()
    value: Any
    if spec.object_type.is_binary or (not spec.object_type.is_analog and m.type == "boolean"):
        value = _is_truthy(present_value)
    elif spec.object_type.is_multistate or m.type in ("unsigned", "enum"):
        value = int(present_value)
    else:
        if not m.scale:
            raise ValueError(f"{spec.point_id}: command mapping scale must be non-zero")
        value = (float(present_value) - m.offset) / m.scale
    return json.dumps({"value": value}).encode("utf-8")
