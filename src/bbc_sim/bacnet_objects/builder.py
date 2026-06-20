"""Build bacpypes3 local objects from the simulator.yaml model (PR-F-012..014).

Maps each BacnetObjectSpec to the matching bacpypes3 local object with its type's
required properties (requirements §10). Output objects (AO/BO/MO) are supported when
explicitly typed (ADR-007).
"""

from __future__ import annotations

import asyncio
from typing import Any

from bacpypes3.apdu import (
    ConfirmedCOVNotificationRequest,
    UnconfirmedCOVNotificationRequest,
)
from bacpypes3.basetypes import PropertyValue as _PropertyValue
from bacpypes3.constructeddata import Any as _Any
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
from bacpypes3.local.cov import COVDetection, GenericCriteria
from bacpypes3.local.device import DeviceObject
from bacpypes3.local.multistate import (
    MultiStateInputObject as _MultiStateInputObject,
    MultiStateOutputObject as _MultiStateOutputObject,
    MultiStateValueObject as _MultiStateValueObject,
)


class MultiStateInputObject(_MultiStateInputObject):
    _cov_criteria = GenericCriteria


class MultiStateOutputObject(_MultiStateOutputObject):
    _cov_criteria = GenericCriteria


class MultiStateValueObject(_MultiStateValueObject):
    _cov_criteria = GenericCriteria


def _safe_send_cov_notifications(self, subscription=None) -> None:
    """Patched COVDetection.send_cov_notifications.

    Fixes bacpypes3 bug: under load, cancel_handle.when() - current_time can be
    negative (timer elapsed but asyncio callback not yet fired), producing a
    negative time_remaining that Unsigned.cast() rejects with ValueError("unsigned").
    max(1, ...) clamps expired handles to 1 s, matching the original intent of the
    "at least one second" guard.
    """
    if not self.cov_subscriptions:
        return

    list_of_values = []
    for property_name in self.properties_reported:
        list_of_values.append(
            _PropertyValue(
                propertyIdentifier=property_name,
                value=_Any(getattr(self, property_name)),
            )
        )

    notification_list = (
        [subscription] if subscription is not None else self.cov_subscriptions
    )
    current_time = asyncio.get_running_loop().time()

    device_object = None
    for obj in self.obj._app.objectIdentifier.values():
        if not isinstance(obj, DeviceObject):
            continue
        if device_object is not None:
            raise RuntimeError("duplicate device object")
        device_object = obj
    if device_object is None:
        raise RuntimeError("missing device object")

    for cov in notification_list:
        if not cov.cancel_handle:
            time_remaining = 0
        else:
            time_remaining = max(1, int(cov.cancel_handle.when() - current_time))

        request = (
            ConfirmedCOVNotificationRequest()
            if cov.confirmed
            else UnconfirmedCOVNotificationRequest()
        )

        request.pduDestination = cov.client_addr
        request.subscriberProcessIdentifier = cov.proc_id
        request.initiatingDeviceIdentifier = device_object.objectIdentifier
        request.monitoredObjectIdentifier = cov.obj_id
        request.timeRemaining = time_remaining
        request.listOfValues = list_of_values

        self.obj._app.cov_notification(cov, request)


COVDetection.send_cov_notifications = _safe_send_cov_notifications

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


def spec_to_oid(spec: BacnetObjectSpec) -> ObjectIdentifier:
    """The bacpypes3 ObjectIdentifier for a spec ((type token, instance)).

    Single source of truth for OID construction — used by the builder, the
    runtime application, southbound bindings, point-list reload, the REST API,
    and the web UI so the mapping never drifts between call sites (EP-009.2).
    """
    return ObjectIdentifier((_OID_TYPE[spec.object_type], spec.object_instance))


def oid_key(spec: BacnetObjectSpec) -> tuple[str, int]:
    """The (dash-style type, instance) tuple used to key writable/command sets.

    ``str(oid[0])`` renders the dash-style token (e.g. "analog-input") that
    BBCApplication compares against in its WriteProperty enforcement, so the
    writable-OID set and the southbound command map must use the same key.
    """
    return (str(spec_to_oid(spec)[0]), spec.object_instance)


def _binary_pv(value: Any) -> str:
    if isinstance(value, str):
        return value if value in ("active", "inactive") else "inactive"
    return "active" if value else "inactive"


def build_object(spec: BacnetObjectSpec) -> Object:
    """Build a single bacpypes3 object with its required properties."""
    cls = _CLASSES[spec.object_type]
    oid = spec_to_oid(spec)
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

    obj = cls(**kwargs)
    if spec.tags:
        from bacpypes3.basetypes import NameValue

        obj.tags = [NameValue(name=t) for t in spec.tags]
    return obj


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
    """Build the NetworkPort describing the BACnet/IP datalink.

    Applies Foreign Device Registration (foreign_bbmd) or BBMD mode (bbmd_bdt) for
    cross-subnet discovery (requirements §12, PR-F-041).
    """
    address = f"{network.bind_address}:{network.port}"
    np = NetworkPortObject(
        address,
        objectIdentifier=("network-port", 1),
        objectName="NetworkPort-1",
    )
    if network.foreign_bbmd:
        from bacpypes3.basetypes import HostNPort, IPMode

        np.bacnetIPMode = IPMode.foreign
        np.fdBBMDAddress = HostNPort(network.foreign_bbmd)
        np.fdSubscriptionLifetime = network.foreign_ttl
    elif network.bbmd_bdt:
        from bacpypes3.basetypes import BDTEntry, IPMode

        np.bacnetIPMode = IPMode.bbmd
        np.bbmdAcceptFDRegistrations = True
        np.bbmdForeignDeviceTable = []
        np.bbmdBroadcastDistributionTable = [BDTEntry(addr) for addr in network.bbmd_bdt]
    return np


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
