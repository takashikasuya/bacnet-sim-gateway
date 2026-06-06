"""Generate the simulator.yaml intermediate model from SBCO points.

device-mapping = aggregated (MVP-1, ADR-011): the entire point list becomes one
Virtual B-BC (one BACnet Device). Object instances are honored from
`instance_no_bacnet` when present, otherwise auto-assigned per object-type namespace
without collisions.
"""

from __future__ import annotations

from collections import defaultdict

from bbc_sim.models import (
    BacnetObjectSpec,
    BacnetObjectType,
    BbcConfig,
    NetworkConfig,
    SbcoPoint,
    SimulatorConfig,
    UpdateConfig,
)
from bbc_sim.semantic.brick import derive_tags, has_mapping
from bbc_sim.yaml_generator.mapping import resolve_object_type
from bbc_sim.yaml_generator.units import to_bacnet_units


def _default_present_value(ot: BacnetObjectType, point: SbcoPoint) -> float | int | bool:
    if ot.is_analog:
        # Start at 0.0, clamped into [min, max] when those bounds exclude it.
        value = 0.0
        if point.min_pres_value is not None and value < point.min_pres_value:
            value = float(point.min_pres_value)
        if point.max_pres_value is not None and value > point.max_pres_value:
            value = float(point.max_pres_value)
        return value
    if ot.is_binary:
        return False
    return 1  # multi-state: states are 1-based


def _assign_instances(
    pairs: list[tuple[SbcoPoint, BacnetObjectType]],
) -> tuple[dict[str, int], list[str]]:
    """Return (point_id -> object_instance, warnings).

    Explicit `instance_no_bacnet` values are honored per object-type namespace. A
    duplicate explicit value within a type is a point-list error; rather than emit an
    invalid model we warn and auto-assign the colliding point.
    """
    used: dict[BacnetObjectType, set[int]] = defaultdict(set)
    result: dict[str, int] = {}
    warnings: list[str] = []

    # First pass: explicit instance numbers (skip duplicates within a type).
    for point, ot in pairs:
        if point.instance_no_bacnet is None:
            continue
        inst = point.instance_no_bacnet
        if inst in used[ot]:
            warnings.append(
                f"{point.point_id}: explicit instance {ot.value}:{inst} already in use; "
                "auto-assigning instead"
            )
            continue
        used[ot].add(inst)
        result[point.point_id] = inst

    # Second pass: auto-assign, skipping used numbers within the type.
    counters: dict[BacnetObjectType, int] = defaultdict(lambda: 1)
    for point, ot in pairs:
        if point.point_id in result:
            continue
        n = counters[ot]
        while n in used[ot]:
            n += 1
        used[ot].add(n)
        counters[ot] = n + 1
        result[point.point_id] = n
    return result, warnings


def generate_config(
    points: list[SbcoPoint],
    *,
    bbc_id: str,
    device_id: int,
    object_name: str = "Local Virtual B-BC",
) -> tuple[SimulatorConfig, list[str]]:
    """Build a SimulatorConfig from points (aggregated). Returns (config, warnings).

    `bbc_id` and `device_id` are supplied by the caller (CLI) and never derived from
    `gateway_id` (ADR-003).
    """
    warnings: list[str] = []
    pairs: list[tuple[SbcoPoint, BacnetObjectType]] = []
    for p in points:
        ot, w = resolve_object_type(p)
        warnings.extend(w)
        pairs.append((p, ot))

    instances, instance_warnings = _assign_instances(pairs)
    warnings.extend(instance_warnings)

    objects: list[BacnetObjectSpec] = []
    for p, ot in pairs:
        units = None
        if ot.is_analog:
            units, uw = to_bacnet_units(p.unit)
            if uw:
                warnings.append(f"{p.point_id}: {uw}")

        active_text = inactive_text = None
        state_text: list[str] = []
        if ot.is_binary and len(p.labels) == 2:
            inactive_text, active_text = p.labels[0], p.labels[1]
        elif ot.is_multistate:
            state_text = list(p.labels)

        # Brick-derived BACnet semantic tags (ADR-012). search_tags is the SBCO `tags`
        # column kept verbatim apart from order-preserving de-duplication.
        search_tags = list(dict.fromkeys(p.tags))
        tags = derive_tags(p.device_type, p.point_type)
        if not has_mapping(p.device_type, p.point_type):
            warnings.append(
                f"{p.point_id}: no Brick seed mapping for device_type="
                f"{p.device_type!r}/point_type={p.point_type!r}; tags limited to base"
            )

        objects.append(
            BacnetObjectSpec(
                point_id=p.point_id,
                object_type=ot,
                object_instance=instances[p.point_id],
                object_name=p.point_name,
                present_value=_default_present_value(ot, p),
                units=units,
                min_pres_value=p.min_pres_value,
                max_pres_value=p.max_pres_value,
                state_text=state_text,
                active_text=active_text,
                inactive_text=inactive_text,
                scale=p.scale,
                writable=p.writable,
                description=p.description,
                update=UpdateConfig(interval=p.interval),
                tags=tags,
                metadata={
                    "gateway_id": p.gateway_id,
                    "device_id": p.device_id,
                    "device_name": p.device_name,
                    "device_type": p.device_type,
                    "point_type": p.point_type,
                    "building": p.building,
                    "floor": p.floor,
                    "installation_area": p.installation_area,
                    "local_id": p.local_id,
                    "search_tags": search_tags,  # SBCO `tags` column, verbatim (deduped)
                },
            )
        )

    config = SimulatorConfig(
        bbc=BbcConfig(bbc_id=bbc_id, device_id=device_id, object_name=object_name),
        network=NetworkConfig(),
        objects=objects,
    )
    return config, warnings
