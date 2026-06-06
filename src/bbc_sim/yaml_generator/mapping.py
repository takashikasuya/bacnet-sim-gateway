"""Object-type resolution for SBCO points (ADR-007, sbco-to-bacnet-mapping §2).

`point_type` is a semantic profile name, not a datatype; the BACnet object type is
taken from `object_type_bacnet` when present, otherwise inferred (with a warning) from
labels / unit / point_specification.
"""

from __future__ import annotations

from bbc_sim.models import BacnetObjectType, SbcoPoint
from bbc_sim.yaml_generator.units import to_bacnet_units

# Normalization for explicit object_type_bacnet, absorbing notation variants.
_EXPLICIT_ALIASES: dict[str, BacnetObjectType] = {
    "analog-input": BacnetObjectType.analogInput,
    "analoginput": BacnetObjectType.analogInput,
    "ai": BacnetObjectType.analogInput,
    "analog-output": BacnetObjectType.analogOutput,
    "analogoutput": BacnetObjectType.analogOutput,
    "ao": BacnetObjectType.analogOutput,
    "analog-value": BacnetObjectType.analogValue,
    "analogvalue": BacnetObjectType.analogValue,
    "av": BacnetObjectType.analogValue,
    "binary-input": BacnetObjectType.binaryInput,
    "binaryinput": BacnetObjectType.binaryInput,
    "bi": BacnetObjectType.binaryInput,
    "binary-output": BacnetObjectType.binaryOutput,
    "binaryoutput": BacnetObjectType.binaryOutput,
    "bo": BacnetObjectType.binaryOutput,
    "binary-value": BacnetObjectType.binaryValue,
    "binaryvalue": BacnetObjectType.binaryValue,
    "bv": BacnetObjectType.binaryValue,
    "multi-state-input": BacnetObjectType.multiStateInput,
    "multistateinput": BacnetObjectType.multiStateInput,
    "mi": BacnetObjectType.multiStateInput,
    "multi-state-output": BacnetObjectType.multiStateOutput,
    "multistateoutput": BacnetObjectType.multiStateOutput,
    "mo": BacnetObjectType.multiStateOutput,
    "multi-state-value": BacnetObjectType.multiStateValue,
    "multistatevalue": BacnetObjectType.multiStateValue,
    "mv": BacnetObjectType.multiStateValue,
}

_ANALOG_SPECS = {"measurement", "metering", "setpoint"}
_BINARY_SPECS = {"status", "alarm"}
_WRITABLE_SPECS = {"command", "setpoint"}


def normalize_object_type(raw: str) -> BacnetObjectType | None:
    """Normalize an explicit object_type_bacnet string; None if unrecognized."""
    return _EXPLICIT_ALIASES.get(raw.strip().lower())


def _family_to_concrete(family: str, writable: bool) -> BacnetObjectType:
    """Map an inferred family ('analog'|'binary'|'multistate') + writability.

    Inference never produces Output objects (ADR-007 rule 4): writable -> Value.
    """
    suffix = "Value" if writable else "Input"
    return BacnetObjectType(f"{family}{suffix}")


def resolve_object_type(point: SbcoPoint) -> tuple[BacnetObjectType, list[str]]:
    """Return (object_type, warnings) for a point.

    Explicit `object_type_bacnet` wins; otherwise infer and warn so the point list
    can be made explicit.
    """
    warnings: list[str] = []

    explicit = point.object_type_bacnet.strip()
    if explicit:
        ot = normalize_object_type(explicit)
        if ot is None:
            warnings.append(
                f"{point.point_id}: unknown object_type_bacnet {explicit!r}; inferring"
            )
        else:
            warnings += _consistency_warnings(point, ot)
            return ot, warnings

    spec = point.point_specification.strip().lower()
    has_numeric_unit = bool(to_bacnet_units(point.unit)[0] != "noUnits")

    if len(point.labels) >= 3:
        family = "multiState"
    elif len(point.labels) == 2:
        family = "binary"
    elif has_numeric_unit or spec in _ANALOG_SPECS:
        family = "analog"
    elif spec in _BINARY_SPECS:
        family = "binary"
    else:
        family = "analog"
        warnings.append(
            f"{point.point_id}: could not infer object type; defaulting to Analog. "
            "Set object_type_bacnet to be explicit."
        )

    ot = _family_to_concrete(family, point.writable)
    warnings.insert(
        0,
        f"{point.point_id}: object_type_bacnet not set; inferred {ot.value}. "
        "Set object_type_bacnet to be explicit.",
    )
    warnings += _consistency_warnings(point, ot)
    return ot, warnings


def _consistency_warnings(point: SbcoPoint, ot: BacnetObjectType) -> list[str]:
    out: list[str] = []
    spec = point.point_specification.strip().lower()
    if spec in _WRITABLE_SPECS and not point.writable:
        out.append(
            f"{point.point_id}: point_specification={point.point_specification!r} "
            "implies writable, but writable=false"
        )
    return out
