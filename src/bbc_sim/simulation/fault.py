"""Fault injection (requirements §11, TS-11, PR-F-031, AC-11).

Reproduces failure modes that are hard to trigger on real equipment:
comm-loss, value freeze, abnormal value, out-of-service, and fault state.
Faults mutate the live BACnet object so northbound reads observe them; freeze/comm-loss
also suppress simulated updates via the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from bacpypes3.object import Object

# statusFlags = [in-alarm, fault, overridden, out-of-service]
_NORMAL_FLAGS = [0, 0, 0, 0]


class FaultType(StrEnum):
    comm_loss = "comm_loss"
    freeze = "freeze"
    abnormal = "abnormal"
    out_of_service = "out_of_service"
    fault = "fault"
    clear = "clear"


@dataclass
class FaultState:
    frozen: bool = False
    comm_loss: bool = False


def _key(obj: Object) -> tuple[str, int]:
    return (str(obj.objectIdentifier[0]), int(obj.objectIdentifier[1]))


def _set_flags(obj: Object, in_alarm: int, fault: int, overridden: int, oos: int) -> None:
    obj.statusFlags = [in_alarm, fault, overridden, oos]


class FaultController:
    """Track and apply faults per object; the engine consults suppression state."""

    def __init__(self) -> None:
        self._states: dict[tuple[str, int], FaultState] = {}

    def state(self, obj: Object) -> FaultState:
        return self._states.setdefault(_key(obj), FaultState())

    def is_suppressed(self, obj: Object) -> bool:
        """Whether simulated updates should be skipped (freeze / comm-loss)."""
        fs = self._states.get(_key(obj))
        return bool(fs and (fs.frozen or fs.comm_loss))

    def apply(self, obj: Object, fault: FaultType, value: Any = None) -> None:
        fs = self.state(obj)
        if fault is FaultType.out_of_service:
            obj.outOfService = True
            _set_flags(obj, 0, 0, 0, 1)
        elif fault is FaultType.fault:
            obj.eventState = "fault"
            _trySet(obj, "reliability", "unreliable-other")
            _set_flags(obj, 0, 1, 0, 0)
        elif fault is FaultType.comm_loss:
            fs.comm_loss = True
            _trySet(obj, "reliability", "communication-failure")
            _set_flags(obj, 0, 1, 0, 0)
        elif fault is FaultType.freeze:
            fs.frozen = True
        elif fault is FaultType.abnormal:
            obj.presentValue = value if value is not None else _abnormal_value(obj)
        elif fault is FaultType.clear:
            fs.frozen = False
            fs.comm_loss = False
            obj.outOfService = False
            _trySet(obj, "eventState", "normal")
            _trySet(obj, "reliability", "no-fault-detected")
            _set_flags(obj, *_NORMAL_FLAGS)


def _abnormal_value(obj: Object) -> float:
    hi = getattr(obj, "maxPresValue", None)
    return float(hi) + 1000.0 if hi is not None else 99999.0


def _trySet(obj: Object, attr: str, value: Any) -> None:
    try:
        setattr(obj, attr, value)
    except Exception:  # noqa: BLE001 - some object types lack reliability/eventState
        pass
