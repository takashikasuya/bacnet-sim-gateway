"""EP-001.2 — column->object mapping + object-type inference (ADR-007, PR-F-005/006)."""

from __future__ import annotations

from bbc_sim.models import BacnetObjectType, SbcoPoint
from bbc_sim.yaml_generator.mapping import resolve_object_type
from bbc_sim.yaml_generator.pointlist import read_point_list
from bbc_sim.yaml_generator.units import to_bacnet_units


def _point(**kw) -> SbcoPoint:
    base = dict(
        gateway_id="GW", device_id="D", device_name="d", device_type="t",
        site="", building="", floor="", installation_area="", target_area="",
        panel="", point_type="", point_specification="", point_id="P",
        point_name="n", writable=False, interval=None, unit="", max_pres_value=None,
        min_pres_value=None, labels=[], scale=1.0, tags=[], supplier="", owner="",
        description="", local_id="", device_id_bacnet="", instance_no_bacnet=None,
        object_type_bacnet="",
    )
    base.update(kw)
    return SbcoPoint(**base)  # type: ignore[arg-type]


def test_explicit_bacnet_type_takes_priority_no_warning():
    p = _point(object_type_bacnet="Binary-Output", labels=["a", "b", "c"])
    ot, warnings = resolve_object_type(p)
    assert ot is BacnetObjectType.binaryOutput
    assert warnings == []


def test_explicit_type_normalizes_aliases():
    for raw, expected in [
        ("Analog-Input", BacnetObjectType.analogInput),
        ("analogInput", BacnetObjectType.analogInput),
        ("AI", BacnetObjectType.analogInput),
        ("Multi-state-Value", BacnetObjectType.multiStateValue),
    ]:
        ot, _ = resolve_object_type(_point(object_type_bacnet=raw))
        assert ot is expected


def test_infer_multistate_from_three_labels():
    ot, warnings = resolve_object_type(_point(labels=["Low", "Med", "High"]))
    assert ot is BacnetObjectType.multiStateInput
    assert warnings  # inference must warn to prompt explicit typing


def test_infer_binary_from_two_labels():
    ot, _ = resolve_object_type(_point(labels=["Off", "On"]))
    assert ot is BacnetObjectType.binaryInput


def test_infer_analog_from_numeric_unit():
    ot, _ = resolve_object_type(_point(unit="℃", point_specification="Measurement"))
    assert ot is BacnetObjectType.analogInput


def test_writable_makes_value_not_input():
    ot, _ = resolve_object_type(
        _point(unit="℃", point_specification="Setpoint", writable=True)
    )
    assert ot is BacnetObjectType.analogValue


def test_binary_value_when_writable():
    ot, _ = resolve_object_type(_point(labels=["Off", "On"], writable=True))
    assert ot is BacnetObjectType.binaryValue


def test_status_without_unit_infers_binary():
    ot, _ = resolve_object_type(_point(point_specification="Status"))
    assert ot is BacnetObjectType.binaryInput


def test_inconsistency_command_but_not_writable_warns():
    _, warnings = resolve_object_type(
        _point(object_type_bacnet="Binary-Output", point_specification="Command",
               writable=False)
    )
    assert any("writable" in w.lower() for w in warnings)


def test_unit_mapping_known():
    assert to_bacnet_units("℃")[0] == "degreesCelsius"
    assert to_bacnet_units("%RH")[0] == "percentRelativeHumidity"
    assert to_bacnet_units("ppm")[0] == "partsPerMillion"


def test_unit_mapping_unknown_falls_back_with_warning():
    units, warning = to_bacnet_units("furlongs")
    assert units == "noUnits"
    assert warning is not None


def test_resolves_every_fixture_row(sample_pointlist):
    points = read_point_list(sample_pointlist)
    resolved = {p.point_id: resolve_object_type(p)[0] for p in points}
    assert resolved["PT001"] is BacnetObjectType.analogInput
    assert resolved["PT002"] is BacnetObjectType.analogInput   # inferred from %RH
    assert resolved["PT003"] is BacnetObjectType.binaryInput   # 2 labels
    assert resolved["PT004"] is BacnetObjectType.binaryOutput  # explicit
    assert resolved["PT005"] is BacnetObjectType.multiStateInput  # 3 labels
    assert resolved["PT006"] is BacnetObjectType.analogValue   # explicit
    assert resolved["PT007"] is BacnetObjectType.multiStateValue  # explicit
    assert resolved["PT008"] is BacnetObjectType.analogInput
