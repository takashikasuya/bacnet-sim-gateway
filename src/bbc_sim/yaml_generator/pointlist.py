"""Read and validate SBCO standard point lists (requirements §5).

The point list is the only input (ADR-001). `gateway_id` is preserved as
metadata and must never be reused as the BACnet device id (ADR-003).
"""

from __future__ import annotations

import csv
from pathlib import Path

from bbc_sim.models import LABEL_SEP, REQUIRED_COLUMNS, PointListError, SbcoPoint

_TRUE = {"true", "1", "yes", "y", "on"}
_FALSE = {"false", "0", "no", "n", "off", ""}


def _norm_bool(value: str) -> bool:
    v = value.strip().lower()
    if v in _TRUE:
        return True
    if v in _FALSE:
        return False
    raise PointListError(f"cannot interpret writable value: {value!r}")


def _opt_int(value: str) -> int | None:
    v = value.strip()
    return int(v) if v else None


def _opt_float(value: str) -> float | None:
    v = value.strip()
    return float(v) if v else None


def _split(value: str) -> list[str]:
    v = value.strip()
    if not v:
        return []
    return [part.strip() for part in v.split(LABEL_SEP) if part.strip()]


def _row_to_point(row: dict[str, str]) -> SbcoPoint:
    g = lambda k: (row.get(k) or "").strip()  # noqa: E731
    scale_raw = g("scale")
    return SbcoPoint(
        gateway_id=g("gateway_id"),
        device_id=g("device_id"),
        device_name=g("device_name"),
        device_type=g("device_type"),
        site=g("site"),
        building=g("building"),
        floor=g("floor"),
        installation_area=g("installation_area"),
        target_area=g("target_area"),
        panel=g("panel"),
        point_type=g("point_type"),
        point_specification=g("point_specification"),
        point_id=g("point_id"),
        point_name=g("point_name"),
        writable=_norm_bool(g("writable")),
        interval=_opt_int(g("interval")),
        unit=g("unit"),
        max_pres_value=_opt_float(g("max_pres_value")),
        min_pres_value=_opt_float(g("min_pres_value")),
        labels=_split(g("labels")),
        scale=float(scale_raw) if scale_raw else 1.0,
        tags=_split(g("tags")),
        supplier=g("supplier"),
        owner=g("owner"),
        description=g("description"),
        local_id=g("local_id"),
        device_id_bacnet=g("device_id_bacnet"),
        instance_no_bacnet=_opt_int(g("instance_no_bacnet")),
        object_type_bacnet=g("object_type_bacnet"),
    )


def read_point_list(path: str | Path) -> list[SbcoPoint]:
    """Read an SBCO point list CSV into typed rows.

    Raises PointListError on structural problems (missing required columns,
    malformed writable values).
    """
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        missing = [c for c in REQUIRED_COLUMNS if c not in header]
        if missing:
            raise PointListError(f"missing required column(s): {', '.join(missing)}")
        return [_row_to_point(row) for row in reader]


def validate_point_list(path: str | Path) -> list[str]:
    """Return a list of human-readable validation errors (empty == valid).

    Structural failures are surfaced as a single error rather than raising,
    so callers (the CLI) can report all problems at once.
    """
    errors: list[str] = []
    try:
        points = read_point_list(path)
    except PointListError as exc:
        return [str(exc)]

    seen: set[str] = set()
    for p in points:
        if not p.point_id:
            errors.append("row with empty point_id")
            continue
        if p.point_id in seen:
            errors.append(f"duplicate point_id: {p.point_id}")
        seen.add(p.point_id)
    return errors
