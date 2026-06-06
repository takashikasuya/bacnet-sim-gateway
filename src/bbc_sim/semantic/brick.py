"""Derive BACnet semantic tags from SBCO device_type / point_type (ADR-012).

The SBCO ontology is Brick/REC-based: device_type maps to a Brick Equipment class and
point_type to a Brick Point class. From those classes we derive a deterministic set of
Project Haystack marker tags via an explicit seed table (no auto-guessing, ADR-006).

This is distinct from the SBCO `tags` column (building-OS *search* tags), which is kept
verbatim in metadata.search_tags.
"""

from __future__ import annotations

# device_type (Brick Equipment class) -> equipment marker tags
_DEVICE_SEED: dict[str, list[str]] = {
    "AirHandlingUnit": ["ahu", "equip"],
    "AHU": ["ahu", "equip"],
    "VAV": ["vav", "equip"],
    "Sensor": ["equip"],
    "Meter": ["meter", "equip"],
    "Chiller": ["chiller", "equip"],
    "Boiler": ["boiler", "equip"],
}

# point_type (Brick Point class) -> point marker tags (Haystack vocabulary)
_POINT_SEED: dict[str, list[str]] = {
    # Temperature/Humidity align with sbco-to-bacnet-mapping.md §6.5 worked example
    # (室温センサ -> point, sensor, temp, air, zone).
    "Temperature": ["sensor", "temp", "air", "zone"],
    "Humidity": ["sensor", "humidity", "air"],
    "CO2 Concentration": ["sensor", "co2", "air"],
    "Illuminance": ["sensor", "illuminance"],
    "Motion": ["sensor", "occupancy"],
    "Flow Rate": ["sensor", "flow"],
    "HVAC Control": ["cmd", "hvac"],
    "Setpoint": ["sp"],
    "Power": ["sensor", "power", "elec"],
    "Energy": ["sensor", "energy", "elec"],
}


def derive_tags(device_type: str, point_type: str) -> list[str]:
    """Return a deterministic, sorted, de-duplicated tag set for an object.

    Always includes the ``point`` marker. Unknown device/point types contribute no
    markers (callers may warn); the result is still valid.
    """
    tags: set[str] = {"point"}
    tags.update(_POINT_SEED.get(point_type.strip(), []))
    tags.update(_DEVICE_SEED.get(device_type.strip(), []))
    return sorted(tags)


def has_mapping(device_type: str, point_type: str) -> bool:
    """Whether either the device_type or point_type has a Brick seed mapping."""
    return point_type.strip() in _POINT_SEED or device_type.strip() in _DEVICE_SEED
