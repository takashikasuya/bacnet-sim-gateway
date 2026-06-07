"""FastAPI control-plane for a running B-BC (requirements §17, PR-F-050).

Read object/device state, write present values, and change scenarios / inject faults at
runtime. This is a side-channel for tests and operators; the northbound protocol stays
BACnet/IP.  EP-007 extends this with /status/*, /bindings, /logs, /pointlist, /mode
endpoints and mounts the server-rendered Web UI under /ui.
"""

from __future__ import annotations

from typing import Any

from bacpypes3.primitivedata import ObjectIdentifier
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from bbc_sim.bacnet_objects.builder import spec_to_oid
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
    *,
    status: Any | None = None,  # StatusProvider | None
    reloader: Any | None = None,  # PointListReloader | None
    ui_enabled: bool = False,
) -> FastAPI:
    faults = faults or FaultController()
    api = FastAPI(title="bbc-sim control")

    # Dynamic lookup so object list stays current after point-list reload (EP-007.4)
    def _specs() -> dict[str, Any]:
        return {s.point_id: s for s in config.objects}

    def _oid(point_id: str, specs: dict[str, Any]) -> ObjectIdentifier:
        return spec_to_oid(specs[point_id])

    def _object_view(point_id: str, specs: dict[str, Any] | None = None) -> dict[str, Any]:
        if specs is None:
            specs = _specs()
        spec = specs[point_id]
        obj = app.get_object_id(_oid(point_id, specs))
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

    # ---- existing endpoints (unchanged behaviour) ----

    @api.get("/devices")
    def devices() -> list[dict[str, Any]]:
        return [
            {
                "device_id": config.bbc.device_id,
                "bbc_id": config.bbc.bbc_id,
                "object_name": config.bbc.object_name,
            }
        ]

    @api.get("/devices/{device_id}")
    def device(device_id: int) -> dict[str, Any]:
        if device_id != config.bbc.device_id:
            raise HTTPException(404, "unknown device")
        return {
            "device_id": config.bbc.device_id,
            "bbc_id": config.bbc.bbc_id,
            "objects": len(config.objects),
        }

    @api.get("/objects")
    def objects() -> list[dict[str, Any]]:
        specs = _specs()
        return [_object_view(p, specs) for p in specs]

    @api.get("/objects/{point_id}")
    def get_object(point_id: str) -> dict[str, Any]:
        specs = _specs()
        if point_id not in specs:
            raise HTTPException(404, "unknown object")
        return _object_view(point_id, specs)

    @api.post("/objects/{point_id}/write")
    def write_object(point_id: str, body: WriteRequest) -> dict[str, Any]:
        specs = _specs()
        if point_id not in specs:
            raise HTTPException(404, "unknown object")
        spec = specs[point_id]
        if not spec.writable:
            raise HTTPException(409, "object is not writable")
        obj = app.get_object_id(_oid(point_id, specs))
        if obj is None:
            raise HTTPException(404, "object not present in runtime")
        try:
            obj.presentValue = body.value
        except (ValueError, TypeError) as exc:
            raise HTTPException(400, f"invalid value for {point_id}: {exc}") from exc
        return _object_view(point_id, specs)

    @api.post("/simulation/scenario")
    def scenario(body: ScenarioRequest) -> dict[str, Any]:
        specs = _specs()
        if body.point_id not in specs:
            raise HTTPException(404, "unknown object")
        obj = app.get_object_id(_oid(body.point_id, specs))
        if obj is None:
            raise HTTPException(404, "object not present in runtime")
        if body.fault:
            try:
                fault = FaultType(body.fault)
            except ValueError as exc:
                raise HTTPException(400, f"unknown fault: {body.fault}") from exc
            try:
                faults.apply(obj, fault, body.value)
            except (ValueError, TypeError) as exc:
                raise HTTPException(400, f"could not apply fault: {exc}") from exc
        elif body.value is not None:
            try:
                obj.presentValue = body.value
            except (ValueError, TypeError) as exc:
                raise HTTPException(400, f"invalid value: {exc}") from exc
        return _object_view(body.point_id, specs)

    # ---- EP-007 new endpoints ----

    def _need_status() -> Any:
        if status is None:
            raise HTTPException(503, "status provider not configured")
        return status

    def _need_reloader() -> Any:
        if reloader is None:
            raise HTTPException(503, "reloader not configured")
        return reloader

    @api.get("/status")
    def runtime_status() -> dict[str, Any]:
        return _need_status().runtime_status()

    @api.get("/status/northbound")
    def northbound_status() -> dict[str, Any]:
        return _need_status().northbound_status()

    @api.get("/status/southbound")
    def southbound_status() -> dict[str, Any]:
        return _need_status().southbound_status()

    @api.get("/bindings")
    def bindings() -> list[dict[str, Any]]:
        if status is None:
            raise HTTPException(503, "status provider not configured")
        sb = status.southbound_status()
        if not sb.get("active"):
            return []
        return sb.get("points", [])

    @api.get("/logs")
    def logs(
        level: str | None = None,
        since: float | None = None,
        limit: int | None = 200,
    ) -> list[dict[str, Any]]:
        if status is None or status.log_handler is None:
            return []
        entries = status.log_handler.snapshot(level=level, since=since, limit=limit)
        return [
            {"ts": e.ts, "level": e.level, "logger": e.logger, "message": e.message}
            for e in entries
        ]

    @api.get("/pointlist")
    def pointlist_info() -> dict[str, Any]:
        return _need_reloader().info()

    @api.post("/pointlist/reload")
    def pointlist_reload() -> dict[str, Any]:
        return _need_reloader().apply()

    @api.post("/mode")
    def set_mode(body: dict[str, str]) -> dict[str, Any]:
        requested = body.get("mode", config.mode.value)
        return {
            "current_mode": config.mode.value,
            "requested_mode": requested,
            "applied": False,
            "restart_required": True,
            "hint": f"bbc-sim run -c <config.yaml> --mode {requested}",
        }

    # ---- EP-007 web UI ----

    if ui_enabled:
        from fastapi.staticfiles import StaticFiles

        from bbc_sim.web.router import create_web_router

        web = create_web_router(config, app, status, reloader)
        api.include_router(web)

        from pathlib import Path as _Path

        _static = _Path(__file__).parent.parent / "web" / "static"
        api.mount("/ui/static", StaticFiles(directory=str(_static)), name="ui-static")

    return api


def _scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    return str(value)
