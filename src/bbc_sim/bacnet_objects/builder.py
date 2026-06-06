"""Build bacpypes3 local objects from the simulator.yaml model (PR-F-012..014).

Maps each BacnetObjectSpec to the matching bacpypes3 local object with its type's
required properties (requirements §10). Output objects (AO/BO/MO) are supported when
explicitly typed (ADR-007).
"""

from __future__ import annotations

from typing import Any

from bacpypes3.local.analog import (
    AnalogInputObject,
    AnalogOutputObject,
    AnalogValueObject,
)
from bacpypes3.local.binary import (
    BinaryInputObject,
    BinaryOutputObject,
    BinaryValueObject,
)
from bacpypes3.local.device import DeviceObject
from bacpypes3.local.multistate import (
    MultiStateInputObject,
    MultiStateOutputObject,
    MultiStateValueObject,
)
from bacpypes3.local.networkport import NetworkPortObject
from bacpypes3.object import Object
from bacpypes3.primitivedata import ObjectIdentifier

from bbc_sim.models import (
    BacnetObjectSpec,
    BacnetObjectType,
    BbcConfig,
    NetworkConfig,
    SimulatorConfig,
)

_CLASSES: dict[BacnetObjectType, type] = {
    BacnetObjectType.analogInput: AnalogInputObject,
    BacnetObjectType.analogOutput: AnalogOutputObject,
    BacnetObjectType.analogValue: AnalogValueObject,
    BacnetObjectType.binaryInput: BinaryInputObject,
    BacnetObjectType.binaryOutput: BinaryOutputObject,
    BacnetObjectType.binaryValue: BinaryValueObject,
    BacnetObjectType.multiStateInput: MultiStateInputObject,
    BacnetObjectType.multiStateOutput: MultiStateOutputObject,
    BacnetObjectType.multiStateValue: MultiStateValueObject,
}

# Object-type tokens passed to bacpypes3 ObjectIdentifier (camelCase, as accepted by
# bacpypes3; note that str(objectIdentifier[0]) renders the dash-style form).
_OID_TYPE: dict[BacnetObjectType, str] = {
    BacnetObjectType.analogInput: "analogInput",
    BacnetObjectType.analogOutput: "analogOutput",
    BacnetObjectType.analogValue: "analogValue",
    BacnetObjectType.binaryInput: "binaryInput",
    BacnetObjectType.binaryOutput: "binaryOutput",
    BacnetObjectType.binaryValue: "binaryValue",
    BacnetObjectType.multiStateInput: "multiStateInput",
    BacnetObjectType.multiStateOutput: "multiStateOutput",
    BacnetObjectType.multiStateValue: "multiStateValue",
}


def _binary_pv(value: Any) -> str:
    if isinstance(value, str):
        return value if value in ("active", "inactive") else "inactive"
    return "active" if value else "inactive"


def build_object(spec: BacnetObjectSpec) -> Object:
    """Build a single bacpypes3 object with its required properties."""
    cls = _CLASSES[spec.object_type]
    oid = ObjectIdentifier((_OID_TYPE[spec.object_type], spec.object_instance))
    kwargs: dict[str, Any] = {
        "objectIdentifier": oid,
        "objectName": spec.object_name,
        "description": spec.description,
        "statusFlags": [0, 0, 0, 0],
        "eventState": "normal",
        "outOfService": False,
    }

    if spec.object_type.is_analog:
        kwargs["presentValue"] = float(spec.present_value or 0.0)
        kwargs["units"] = spec.units or "noUnits"
        kwargs["covIncrement"] = 0.1  # required for present-value COV reporting
        kwargs["resolution"] = 0.1  # required Analog property (§10)
        if spec.min_pres_value is not None:
            kwargs["minPresValue"] = float(spec.min_pres_value)
        if spec.max_pres_value is not None:
            kwargs["maxPresValue"] = float(spec.max_pres_value)
    elif spec.object_type.is_binary:
        kwargs["presentValue"] = _binary_pv(spec.present_value)
        kwargs["polarity"] = "normal"
        if spec.inactive_text is not None:
            kwargs["inactiveText"] = spec.inactive_text
        if spec.active_text is not None:
            kwargs["activeText"] = spec.active_text
    else:  # multi-state
        states = spec.state_text or ["state-1"]
        kwargs["numberOfStates"] = len(states)
        kwargs["stateText"] = list(states)
        pv = int(spec.present_value) if spec.present_value else 1
        kwargs["presentValue"] = max(1, min(pv, len(states)))

    return cls(**kwargs)


def build_device(bbc: BbcConfig) -> DeviceObject:
    """Build the Device object with required properties (requirements §7)."""
    return DeviceObject(
        objectIdentifier=("device", bbc.device_id),
        objectName=bbc.object_name,
        vendorName=bbc.vendor_name,
        vendorIdentifier=bbc.vendor_identifier,
        modelName=bbc.model_name,
        firmwareRevision="0.1.0",
        applicationSoftwareVersion="0.1.0",
    )


def build_network_port(network: NetworkConfig) -> NetworkPortObject:
    """Build the NetworkPort describing the BACnet/IP datalink."""
    address = f"{network.bind_address}:{network.port}"
    return NetworkPortObject(
        address,
        objectIdentifier=("network-port", 1),
        objectName="NetworkPort-1",
    )


def build_object_list(config: SimulatorConfig, *, with_network: bool = True) -> list[Object]:
    """Build [device, (network-port), *objects] for Application.from_object_list.

    ``with_network=False`` omits the BACnet/IP datalink — useful for control-plane
    tests that don't need an event loop / UDP socket.
    """
    objects: list[Object] = [build_device(config.bbc)]
    if with_network:
        objects.append(build_network_port(config.network))
    objects.extend(build_object(spec) for spec in config.objects)
    return objects
