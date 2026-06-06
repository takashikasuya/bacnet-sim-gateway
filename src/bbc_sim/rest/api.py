"""FastAPI control-plane for a running B-BC (requirements §17, PR-F-050).

Read object/device state, write present values, and change scenarios / inject faults at
runtime. This is a side-channel for tests and operators; the northbound protocol stays
BACnet/IP.
"""

from __future__ import annotations

from typing import Any

from bacpypes3.primitivedata import ObjectIdentifier
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from bbc_sim.bacnet_objects.builder import _OID_TYPE
from bbc_sim.models import SimulatorConfig
from bbc_sim.simulation.fault import FaultController, FaultType
from bbc_sim.simulator_runtime.app import BBCApplication


class WriteRequest(BaseModel):
    value: Any


class ScenarioRequest(BaseModel):
    point_id: str
    fault: str | None = None  # comm_loss | freeze | abnormal | out_of_service | fault | clear
    value: Any | None = None  # for fault=abnormal or a direct present-value set


def create_app(
    app: BBCApplication,
    config: SimulatorConfig,
    faults: FaultController | None = None,
) -> FastAPI:
    faults = faults or FaultController()
    api = FastAPI(title="bbc-sim control")
    specs_by_point = {s.point_id: s for s in config.objects}

    def _oid(point_id: str) -> ObjectIdentifier:
        spec = specs_by_point[point_id]
        return ObjectIdentifier((_OID_TYPE[spec.object_type], spec.object_instance))

    def _object_view(point_id: str) -> dict[str, Any]:
        spec = specs_by_point[point_id]
        obj = app.get_object_id(_oid(point_id))
        return {
            "point_id": point_id,
            "object_type": spec.object_type.value,
            "object_instance": spec.object_instance,
            "object_name": spec.object_name,
            "present_value": _scalar(getattr(obj, "presentValue", None)),
            "out_of_service": bool(getattr(obj, "outOfService", False)),
            "status_flags": list(getattr(obj, "statusFlags", []) or []),
            "writable": spec.writable,
        }

    @api.get("/devices")
    def devices() -> list[dict[str, Any]]:
        return [{"device_id": config.bbc.device_id, "bbc_id": config.bbc.bbc_id,
                 "object_name": config.bbc.object_name}]

    @api.get("/devices/{device_id}")
    def device(device_id: int) -> dict[str, Any]:
        if device_id != config.bbc.device_id:
            raise HTTPException(404, "unknown device")
        return {"device_id": config.bbc.device_id, "bbc_id": config.bbc.bbc_id,
                "objects": len(config.objects)}

    @api.get("/objects")
    def objects() -> list[dict[str, Any]]:
        return [_object_view(p) for p in specs_by_point]

    @api.get("/objects/{point_id}")
    def get_object(point_id: str) -> dict[str, Any]:
        if point_id not in specs_by_point:
            raise HTTPException(404, "unknown object")
        return _object_view(point_id)

    @api.post("/objects/{point_id}/write")
    def write_object(point_id: str, body: WriteRequest) -> dict[str, Any]:
        if point_id not in specs_by_point:
            raise HTTPException(404, "unknown object")
        spec = specs_by_point[point_id]
        if not spec.writable:
            raise HTTPException(409, "object is not writable")
        obj = app.get_object_id(_oid(point_id))
        obj.presentValue = body.value
        return _object_view(point_id)

    @api.post("/simulation/scenario")
    def scenario(body: ScenarioRequest) -> dict[str, Any]:
        if body.point_id not in specs_by_point:
            raise HTTPException(404, "unknown object")
        obj = app.get_object_id(_oid(body.point_id))
        if body.fault:
            try:
                fault = FaultType(body.fault)
            except ValueError as exc:
                raise HTTPException(400, f"unknown fault: {body.fault}") from exc
            faults.apply(obj, fault, body.value)
        elif body.value is not None:
            obj.presentValue = body.value
        return _object_view(body.point_id)

    return api


def _scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    return str(value)
