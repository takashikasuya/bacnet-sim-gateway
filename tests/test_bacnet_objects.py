"""EP-001.5 — build bacpypes3 objects from simulator.yaml (PR-F-012..014, §10)."""

from __future__ import annotations

import pytest

from bbc_sim.bacnet_objects.builder import build_device, build_object, build_object_list
from bbc_sim.models import BacnetObjectSpec, BacnetObjectType
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list


def _config(path):
    points = read_point_list(path)
    cfg, _ = generate_config(points, bbc_id="bbc-local-001", device_id=1001)
    return cfg


def test_build_device(sample_pointlist):
    cfg = _config(sample_pointlist)
    dev = build_device(cfg.bbc)
    assert str(dev.objectIdentifier[0]) == "device"
    assert dev.objectIdentifier[1] == 1001
    assert dev.objectName == cfg.bbc.object_name
    assert int(dev.vendorIdentifier) == 999


def test_build_object_list_has_device_and_all_objects(sample_pointlist):
    cfg = _config(sample_pointlist)
    objs = build_object_list(cfg)
    # device + network-port + 8 points
    type_names = [o.objectIdentifier[0] for o in objs]
    assert "device" in [str(t) for t in type_names]
    assert sum(1 for o in objs if str(o.objectIdentifier[0]) not in ("device", "network-port")) == 8


def test_analog_object_properties(sample_pointlist):
    cfg = _config(sample_pointlist)
    pt001 = next(o for o in cfg.objects if o.point_id == "PT001")
    obj = build_object(pt001)
    assert str(obj.objectIdentifier[0]) == "analog-input"
    assert float(obj.presentValue) == 0.0
    assert str(obj.units) == "degrees-celsius"
    assert float(obj.minPresValue) == -10.0
    assert float(obj.maxPresValue) == 50.0


def test_binary_object_text(sample_pointlist):
    cfg = _config(sample_pointlist)
    pt004 = next(o for o in cfg.objects if o.point_id == "PT004")
    obj = build_object(pt004)
    assert str(obj.objectIdentifier[0]) == "binary-output"
    assert obj.inactiveText == "Closed"
    assert obj.activeText == "Open"


def test_multistate_object_states(sample_pointlist):
    cfg = _config(sample_pointlist)
    pt005 = next(o for o in cfg.objects if o.point_id == "PT005")
    obj = build_object(pt005)
    assert str(obj.objectIdentifier[0]) == "multi-state-input"
    assert int(obj.numberOfStates) == 3
    assert list(obj.stateText) == ["Low", "Medium", "High"]


def test_object_instance_preserved(sample_pointlist):
    cfg = _config(sample_pointlist)
    pt001 = next(o for o in cfg.objects if o.point_id == "PT001")
    obj = build_object(pt001)
    assert str(obj.objectIdentifier[0]) == "analog-input"
    assert obj.objectIdentifier[1] == 1001


@pytest.mark.parametrize(
    "object_type,states",
    [
        (BacnetObjectType.multiStateInput, ["Low", "High"]),
        (BacnetObjectType.multiStateOutput, ["Off", "On", "Auto"]),
        (BacnetObjectType.multiStateValue, ["A", "B"]),
    ],
)
def test_multistate_objects_use_generic_cov_criteria(object_type, states):
    """MultiState objects must use GenericCriteria, not COVIncrementCriteria (#75).

    COVIncrementCriteria accesses .covIncrement which MultiState objects don't have;
    bacpypes3 returns operational-problem when a COV subscription is requested.
    """
    from bacpypes3.local.cov import GenericCriteria

    spec = BacnetObjectSpec(
        point_id="TEST-MS",
        object_type=object_type,
        object_instance=1,
        object_name="Test MS",
        state_text=states,
    )
    obj = build_object(spec)
    assert obj._cov_criteria is GenericCriteria, (
        f"{object_type.value} must use GenericCriteria for COV subscriptions"
    )
