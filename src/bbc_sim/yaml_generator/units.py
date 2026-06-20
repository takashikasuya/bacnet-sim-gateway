"""SBCO unit -> BACnet Engineering Units mapping (requirements §3, sbco-to-bacnet §3).

Unknown units fall back to ``noUnits`` with a warning. The table is intentionally
small and extends as new units appear in point lists.
"""

from __future__ import annotations

_UNIT_MAP: dict[str, str] = {
    "℃": "degreesCelsius",
    "degc": "degreesCelsius",
    "celsius": "degreesCelsius",
    "°c": "degreesCelsius",
    "%": "percent",
    "%rh": "percentRelativeHumidity",
    "kw": "kilowatts",
    "kwh": "kilowattHours",
    "pa": "pascals",
    "m3/h": "cubicMetersPerHour",
    "ppm": "partsPerMillion",
    "lux": "luxUnits",
    "lx": "luxUnits",
    "m/s": "metersPerSecond",
    "bar": "bars",
    "bars": "bars",
    "mbar": "millibars",
}

NO_UNITS = "noUnits"


def to_bacnet_units(unit: str) -> tuple[str, str | None]:
    """Return (bacnet_units, warning). Empty unit maps to noUnits silently."""
    key = unit.strip().lower()
    if not key:
        return NO_UNITS, None
    mapped = _UNIT_MAP.get(key)
    if mapped is None:
        return NO_UNITS, f"unknown unit {unit!r}; falling back to noUnits"
    return mapped, None
