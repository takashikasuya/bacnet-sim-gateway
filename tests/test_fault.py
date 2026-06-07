"""EP-003.2 — fault injection (TS-11, PR-F-031, AC-11)."""

from __future__ import annotations

import logging

from bbc_sim.bacnet_objects.builder import build_object
from bbc_sim.models import BacnetObjectSpec, BacnetObjectType
from bbc_sim.simulation import fault as fault_mod
from bbc_sim.simulation.fault import FaultController, FaultType


def _ai() -> object:
    spec = BacnetObjectSpec(
        point_id="P1",
        object_type=BacnetObjectType.analogInput,
        object_instance=1,
        object_name="t",
        present_value=20.0,
        units="degreesCelsius",
        min_pres_value=0.0,
        max_pres_value=40.0,
    )
    return build_object(spec)


def test_out_of_service():
    obj = _ai()
    fc = FaultController()
    fc.apply(obj, FaultType.out_of_service)
    assert bool(obj.outOfService) is True
    assert list(obj.statusFlags)[3] == 1


def test_fault_state_sets_event_and_flags():
    obj = _ai()
    fc = FaultController()
    fc.apply(obj, FaultType.fault)
    assert str(obj.eventState) == "fault"
    assert list(obj.statusFlags)[1] == 1


def test_comm_loss_suppresses_updates():
    obj = _ai()
    fc = FaultController()
    fc.apply(obj, FaultType.comm_loss)
    assert fc.is_suppressed(obj) is True
    assert list(obj.statusFlags)[1] == 1


def test_freeze_suppresses_updates():
    obj = _ai()
    fc = FaultController()
    fc.apply(obj, FaultType.freeze)
    assert fc.is_suppressed(obj) is True


def test_abnormal_value_out_of_range():
    obj = _ai()
    fc = FaultController()
    fc.apply(obj, FaultType.abnormal)
    assert float(obj.presentValue) > 40.0


def test_clear_resets():
    obj = _ai()
    fc = FaultController()
    fc.apply(obj, FaultType.fault)
    fc.apply(obj, FaultType.freeze)
    fc.apply(obj, FaultType.clear)
    assert fc.is_suppressed(obj) is False
    assert bool(obj.outOfService) is False
    assert str(obj.eventState) == "normal"
    assert list(obj.statusFlags) == [0, 0, 0, 0]


def test_tryset_swallows_unsupported_attribute_but_logs(caplog):
    """_trySet must not propagate when a property is unsupported, but should log (EP-009.4)."""

    class _NoReliability:
        @property
        def reliability(self):
            return None

        @reliability.setter
        def reliability(self, value):
            raise AttributeError("object has no reliability")

    obj = _NoReliability()
    with caplog.at_level(logging.DEBUG, logger="bbc_sim.simulation.fault"):
        fault_mod._trySet(obj, "reliability", "unreliable-other")  # must not raise
    assert any("reliability" in r.getMessage() for r in caplog.records)


def test_apply_fault_on_object_without_reliability_does_not_raise():
    """A fault that sets reliability must still set status flags even if the
    object type rejects reliability (the optional property is best-effort)."""

    class _Obj:
        def __init__(self) -> None:
            self.objectIdentifier = ("analogValue", 1)
            self.statusFlags = [0, 0, 0, 0]
            self.eventState = "normal"

        @property
        def reliability(self):
            return None

        @reliability.setter
        def reliability(self, value):
            raise ValueError("unsupported")

    obj = _Obj()
    FaultController().apply(obj, FaultType.fault)  # must not raise
    assert list(obj.statusFlags)[1] == 1  # fault flag still set
