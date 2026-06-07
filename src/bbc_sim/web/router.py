"""Server-rendered admin UI router (EP-007, PR-F-052).

Pages live under /ui/*.  Auto-refresh partials are fetched by app.js setInterval calls
and returned as plain HTML fragments (no full-page reload).  All state comes from the
StatusProvider and PointListReloader — no HTTP self-calls.

Data for partials is built inline in each handler using shared helper functions.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

_HERE = Path(__file__).parent
_templates = Jinja2Templates(directory=str(_HERE / "templates"))

# context helpers consumed by both full pages and partials


def _obj_list(config: Any, app: Any) -> list[dict[str, Any]]:
    from bbc_sim.bacnet_objects.builder import spec_to_oid

    result = []
    for spec in config.objects:
        obj = app.get_object_id(spec_to_oid(spec))
        pv = getattr(obj, "presentValue", None)
        oos = bool(getattr(obj, "outOfService", False))
        flags = list(getattr(obj, "statusFlags", []) or [])
        result.append(
            {
                "point_id": spec.point_id,
                "object_type": spec.object_type.value,
                "object_instance": spec.object_instance,
                "object_name": spec.object_name,
                "present_value": str(pv) if pv is not None else "—",
                "units": spec.units or "",
                "writable": spec.writable,
                "out_of_service": oos,
                "status_flags": flags,
                "has_binding": spec.binding is not None,
            }
        )
    return result


def create_web_router(
    config: Any,
    app: Any,
    status: Any | None,
    reloader: Any | None,
) -> APIRouter:
    router = APIRouter(prefix="/ui")

    def _base_ctx(request: Request) -> dict[str, Any]:
        return {
            "request": request,
            "mode": config.mode.value,
            "bbc_id": config.bbc.bbc_id,
            "device_id": config.bbc.device_id,
            "object_name": config.bbc.object_name,
        }

    # ---- Dashboard ----

    @router.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> Any:
        ctx = _base_ctx(request)
        ctx["page"] = "dashboard"
        if status:
            ctx["runtime"] = status.runtime_status()
            ctx["northbound"] = status.northbound_status()
            ctx["southbound"] = status.southbound_status()
        return _templates.TemplateResponse(request, "dashboard.html", context=ctx)

    @router.get("/partials/tiles", response_class=HTMLResponse)
    def tiles_partial(request: Request) -> Any:
        ctx = _base_ctx(request)
        if status:
            ctx["runtime"] = status.runtime_status()
            ctx["northbound"] = status.northbound_status()
            ctx["southbound"] = status.southbound_status()
        return _templates.TemplateResponse(request, "partials/_tiles.html", context=ctx)

    # ---- Devices & Objects ----

    @router.get("/devices", response_class=HTMLResponse)
    def devices_page(request: Request) -> Any:
        ctx = _base_ctx(request)
        ctx["page"] = "devices"
        ctx["objects"] = _obj_list(config, app)
        return _templates.TemplateResponse(request, "devices.html", context=ctx)

    @router.get("/partials/objects_table", response_class=HTMLResponse)
    def objects_table_partial(request: Request) -> Any:
        ctx = _base_ctx(request)
        ctx["objects"] = _obj_list(config, app)
        return _templates.TemplateResponse(request, "partials/_objects_table.html", context=ctx)

    # ---- Object Detail ----

    @router.get("/objects/{point_id}", response_class=HTMLResponse)
    def object_detail(request: Request, point_id: str) -> Any:
        specs = {s.point_id: s for s in config.objects}
        if point_id not in specs:
            return HTMLResponse("<p>Object not found.</p>", status_code=404)
        rows = _obj_list(config, app)
        obj_data = next((r for r in rows if r["point_id"] == point_id), None)
        spec = specs[point_id]
        ctx = _base_ctx(request)
        ctx.update(
            {
                "page": "devices",
                "obj": obj_data,
                "spec": spec,
                "fault_types": [
                    "comm_loss",
                    "freeze",
                    "abnormal",
                    "out_of_service",
                    "fault",
                    "clear",
                ],
            }
        )
        return _templates.TemplateResponse(request, "object_detail.html", context=ctx)

    # ---- Bindings ----

    @router.get("/bindings", response_class=HTMLResponse)
    def bindings_page(request: Request) -> Any:
        ctx = _base_ctx(request)
        ctx["page"] = "bindings"
        sb = status.southbound_status() if status else {"active": False, "points": []}
        ctx["sb"] = sb
        ctx["points"] = sb.get("points", [])
        return _templates.TemplateResponse(request, "bindings.html", context=ctx)

    @router.get("/partials/bindings_table", response_class=HTMLResponse)
    def bindings_table_partial(request: Request) -> Any:
        ctx = _base_ctx(request)
        sb = status.southbound_status() if status else {"active": False, "points": []}
        ctx["points"] = sb.get("points", [])
        return _templates.TemplateResponse(request, "partials/_bindings_table.html", context=ctx)

    # ---- Status ----

    @router.get("/status", response_class=HTMLResponse)
    def status_page(request: Request) -> Any:
        ctx = _base_ctx(request)
        ctx["page"] = "status"
        if status:
            ctx["northbound"] = status.northbound_status()
            ctx["southbound"] = status.southbound_status()
        return _templates.TemplateResponse(request, "status.html", context=ctx)

    @router.get("/partials/counters", response_class=HTMLResponse)
    def counters_partial(request: Request) -> Any:
        ctx = _base_ctx(request)
        if status:
            ctx["northbound"] = status.northbound_status()
        return _templates.TemplateResponse(request, "partials/_counters.html", context=ctx)

    # ---- Logs ----

    @router.get("/logs", response_class=HTMLResponse)
    def logs_page(request: Request, level: str = "", limit: int = 100) -> Any:
        ctx = _base_ctx(request)
        ctx["page"] = "logs"
        entries: list[dict[str, Any]] = []
        if status and status.log_handler:
            lv = level.upper() if level else None
            raw = status.log_handler.snapshot(level=lv, limit=limit)
            entries = [
                {"ts": e.ts, "level": e.level, "logger": e.logger, "message": e.message}
                for e in reversed(raw)
            ]
        ctx["entries"] = entries
        ctx["selected_level"] = level
        return _templates.TemplateResponse(request, "logs.html", context=ctx)

    @router.get("/partials/logtail", response_class=HTMLResponse)
    def logtail_partial(request: Request, level: str = "", limit: int = 50) -> Any:
        ctx = _base_ctx(request)
        entries: list[dict[str, Any]] = []
        if status and status.log_handler:
            lv = level.upper() if level else None
            raw = status.log_handler.snapshot(level=lv, limit=limit)
            entries = [
                {"ts": e.ts, "level": e.level, "logger": e.logger, "message": e.message}
                for e in reversed(raw)
            ]
        ctx["entries"] = entries
        return _templates.TemplateResponse(request, "partials/_logtail.html", context=ctx)

    # ---- Point list ----

    @router.get("/pointlist", response_class=HTMLResponse)
    def pointlist_page(request: Request) -> Any:
        ctx = _base_ctx(request)
        ctx["page"] = "pointlist"
        ctx["info"] = reloader.info() if reloader else {}
        return _templates.TemplateResponse(request, "pointlist.html", context=ctx)

    @router.post("/pointlist/reload", response_class=HTMLResponse)
    def pointlist_reload(request: Request) -> Any:
        result = reloader.apply() if reloader else {"status": "no_reloader", "errors": []}
        ctx = _base_ctx(request)
        ctx["result"] = result
        ctx["info"] = reloader.info() if reloader else {}
        return _templates.TemplateResponse(request, "partials/_reload_result.html", context=ctx)

    # ---- Help / Onboarding ----

    @router.get("/help", response_class=HTMLResponse)
    def help_page(request: Request) -> Any:
        ctx = _base_ctx(request)
        ctx["page"] = "help"
        return _templates.TemplateResponse(request, "help.html", context=ctx)

    # ---- Context help partials ----

    @router.get("/partials/help/{page_name}", response_class=HTMLResponse)
    def context_help(request: Request, page_name: str) -> Any:
        ctx = _base_ctx(request)
        # Restrict to a conservative charset so the name can never carry markup;
        # never echo the raw URL segment back into the HTML body (reflected-XSS guard).
        if not re.fullmatch(r"[a-z_]{1,40}", page_name):
            return HTMLResponse("<p>Help page not found.</p>", status_code=404)
        tpl = f"partials/_help_{page_name}.html"
        try:
            return _templates.TemplateResponse(request, tpl, context=ctx)
        except Exception:
            return HTMLResponse("<p>Help page not found.</p>", status_code=404)

    return router
