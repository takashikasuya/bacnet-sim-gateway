"""Southbound channel/address derivation (PR-F-090, southbound-binding.md §6).

`local_id` is the first source of the southbound address (it is the field-side point
identifier == the MQTT topic / endpoint). Falls back to building/device/point.
"""

from __future__ import annotations

from bbc_sim.models import BacnetObjectSpec


def derive_address(spec: BacnetObjectSpec) -> str:
    """Channel key for an object. Explicit binding.address wins, then local_id."""
    if spec.binding and spec.binding.address:
        return spec.binding.address
    local_id = str(spec.metadata.get("local_id") or "").strip()
    if local_id:
        return local_id
    building = spec.metadata.get("building") or "_"
    device = spec.metadata.get("device_id") or "_"
    return f"{building}/{device}/{spec.point_id}"


def mqtt_topics(spec: BacnetObjectSpec) -> tuple[str, str]:
    """Return (telemetry_topic, command_topic) per requirements §18.

    Uses building/device/point; an explicit binding.address overrides the base.
    """
    if spec.binding and spec.binding.address:
        base = spec.binding.address.rstrip("/")
    else:
        building = spec.metadata.get("building") or "_"
        device = spec.metadata.get("device_id") or "_"
        base = f"building/{building}/device/{device}/point/{spec.point_id}"
    return f"{base}/telemetry", f"{base}/command"
