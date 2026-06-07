"""BACnet client helpers for discovery and property access (requirements §9, §15).

Used by the client CLIs and tests. A transient client Application is created bound to
a local address; operations are issued against a target B-BC address.
"""

from __future__ import annotations

import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from bacpypes3.app import Application
from bacpypes3.local.device import DeviceObject
from bacpypes3.local.networkport import NetworkPortObject
from bacpypes3.pdu import Address

_CLIENT_DEVICE_ID = 4194300  # high instance, distinct from simulated B-BCs


def ephemeral_local(host: str = "0.0.0.0") -> str:
    """Return a 'host:port' on a free UDP port for a transient client."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((host, 0))
        return f"{host}:{s.getsockname()[1]}"


def build_client(local_address: str, *, device_id: int = _CLIENT_DEVICE_ID) -> Application:
    """Build a minimal client Application bound to ``local_address`` (host:port)."""
    device = DeviceObject(
        objectIdentifier=("device", device_id),
        objectName="bbc-sim-client",
        vendorIdentifier=999,
    )
    network_port = NetworkPortObject(
        local_address,
        objectIdentifier=("network-port", 1),
        objectName="NetworkPort-1",
    )
    return Application.from_object_list([device, network_port])


@asynccontextmanager
async def client_app(local_address: str) -> AsyncIterator[Application]:
    app = build_client(local_address)
    try:
        yield app
    finally:
        app.close()


async def whois(
    app: Application,
    target: str,
    low: int | None = None,
    high: int | None = None,
) -> list[tuple[int, str]]:
    """Send Who-Is and return [(device_instance, address)] from I-Am replies."""
    i_ams = await app.who_is(low, high, Address(target))
    out: list[tuple[int, str]] = []
    for iam in i_ams:
        out.append((iam.iAmDeviceIdentifier[1], str(iam.pduSource)))
    return out


async def read_property(
    app: Application, target: str, objid: str, prop: str = "present-value"
) -> Any:
    return await app.read_property(target, objid, prop)


async def read_property_multiple(
    app: Application, target: str, objid: str, props: list[str]
) -> list[tuple[Any, Any, Any, Any]]:
    # bacpypes3 expects a flat [objid, [props], objid2, [props2], ...] list.
    return await app.read_property_multiple(Address(target), [objid, props])


async def read_present_values(app: Application, target: str, objids: list[str]) -> dict[str, Any]:
    """RPM-read present-value for many objects in one request.

    Returns ``{objid: value}`` keyed by the requested id strings (positional match
    with the response, which bacpypes3 returns in request order). Objects that the
    device reports an error for are omitted so the caller can fall back to a
    per-object read. Raises if the whole RPM request fails.
    """
    from bacpypes3.basetypes import ErrorType

    if not objids:
        return {}
    args: list[Any] = []
    for objid in objids:
        args.extend([objid, ["present-value"]])
    results = await app.read_property_multiple(Address(target), args)
    out: dict[str, Any] = {}
    for objid, result in zip(objids, results, strict=False):
        value = result[3] if isinstance(result, (list, tuple)) and len(result) >= 4 else None
        if value is None or isinstance(value, ErrorType):
            continue  # leave for per-object fallback
        out[objid] = value
    return out


async def write_property(
    app: Application, target: str, objid: str, value: Any, prop: str = "present-value"
) -> None:
    await app.write_property(target, objid, prop, value)


async def write_property_multiple(
    app: Application, target: str, writes: list[tuple[str, Any]], prop: str = "present-value"
) -> None:
    """WritePropertyMultiple: ``writes`` is [(objid, value), ...] (requirements §9)."""
    from bacpypes3.apdu import (
        PropertyValue,
        WriteAccessSpecification,
        WritePropertyMultipleRequest,
    )
    from bacpypes3.constructeddata import Any as BAny
    from bacpypes3.primitivedata import ObjectIdentifier, Real

    specs = []
    for objid, value in writes:
        pv = PropertyValue(propertyIdentifier=prop, value=BAny(Real(float(value))))
        specs.append(
            WriteAccessSpecification(
                objectIdentifier=ObjectIdentifier(objid), listOfProperties=[pv]
            )
        )
    req = WritePropertyMultipleRequest(listOfWriteAccessSpecs=specs)
    req.pduDestination = Address(target)
    await app.request(req)


async def subscribe_cov(
    app: Application,
    target: str,
    objid: str,
    process_id: int = 1,
    confirmed: bool = False,
    lifetime: int = 60,
) -> None:
    """Send SubscribeCOV for an object (requirements §9, PR-F-028)."""
    from bacpypes3.apdu import SubscribeCOVRequest
    from bacpypes3.primitivedata import ObjectIdentifier

    req = SubscribeCOVRequest(
        subscriberProcessIdentifier=process_id,
        monitoredObjectIdentifier=ObjectIdentifier(objid),
        issueConfirmedNotifications=confirmed,
        lifetime=lifetime,
    )
    req.pduDestination = Address(target)
    await app.request(req)


def capture_cov_notifications(app: Application) -> list[tuple[str, str]]:
    """Patch a client app to record COV notifications; returns the growing list."""
    captured: list[tuple[str, str]] = []
    orig_u = app.do_UnconfirmedCOVNotificationRequest
    orig_c = app.do_ConfirmedCOVNotificationRequest

    async def do_u(apdu: Any) -> None:
        captured.append(("unconfirmed", str(apdu.monitoredObjectIdentifier)))
        await orig_u(apdu)

    async def do_c(apdu: Any) -> None:
        captured.append(("confirmed", str(apdu.monitoredObjectIdentifier)))
        await orig_c(apdu)

    app.do_UnconfirmedCOVNotificationRequest = do_u  # type: ignore[method-assign]
    app.do_ConfirmedCOVNotificationRequest = do_c  # type: ignore[method-assign]
    return captured


async def list_objects(app: Application, target: str) -> list[str]:
    """Discover the target B-BC and read its object-list."""
    found = await whois(app, target)
    if not found:
        return []
    device_instance = found[0][0]
    obj_list = await app.read_property(target, f"device,{device_instance}", "object-list")
    return [f"{o[0]},{o[1]}" for o in obj_list]
