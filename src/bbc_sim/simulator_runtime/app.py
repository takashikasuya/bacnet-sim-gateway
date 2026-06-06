"""Single-loop asyncio B-BC runtime (ADR-010).

Builds a bacpypes3 Application from the simulator.yaml model and serves it on
BACnet/IP (northbound, ADR-005). The Core Object Model lives on the event loop;
no blocking calls.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from bacpypes3.apdu import WritePropertyRequest
from bacpypes3.app import Application
from bacpypes3.errors import ExecutionError

from bbc_sim.bacnet_objects.builder import build_object_list
from bbc_sim.models import SimulatorConfig
from bbc_sim.yaml_generator.yaml_io import load_config

_log = logging.getLogger(__name__)

_PRESENT_VALUE = {"present-value", "presentValue"}

CommandHook = Callable[[tuple[str, int], Any], Awaitable[None]]


class BBCApplication(Application):
    """Application that enforces SBCO `writable` on present-value (AC-5).

    Only points marked writable (Value/Output) accept WriteProperty on
    present-value; Inputs reject with writeAccessDenied. A command hook lets the
    southbound manager forward writes to bound objects (command path).
    """

    _writable_oids: frozenset[tuple[str, int]] = frozenset()
    _command_oids: frozenset[tuple[str, int]] = frozenset()
    on_command: CommandHook | None = None

    async def do_WritePropertyRequest(self, apdu: WritePropertyRequest) -> None:
        prop = str(apdu.propertyIdentifier)
        oid = (str(apdu.objectIdentifier[0]), int(apdu.objectIdentifier[1]))
        if prop in _PRESENT_VALUE and oid not in self._writable_oids:
            raise ExecutionError(errorClass="property", errorCode="writeAccessDenied")
        await super().do_WritePropertyRequest(apdu)
        if prop in _PRESENT_VALUE and self.on_command and oid in self._command_oids:
            obj = self.get_object_id(apdu.objectIdentifier)
            if obj is not None:
                await self.on_command(oid, obj.presentValue)


def build_application(config: SimulatorConfig) -> BBCApplication:
    """Build the BACnet/IP Application. Must be called inside a running event loop."""
    objects = build_object_list(config)
    app = BBCApplication.from_object_list(objects)
    # objects = [device, network-port, *config.objects] in order.
    point_objects = objects[2:]
    app._writable_oids = frozenset(
        (str(obj.objectIdentifier[0]), int(obj.objectIdentifier[1]))
        for obj, spec in zip(point_objects, config.objects, strict=True)
        if spec.writable
    )
    return app


async def run_async(
    config: SimulatorConfig,
    stop: asyncio.Event | None = None,
    transport_uri: str | None = None,
) -> None:
    """Run the B-BC until ``stop`` is set (or forever).

    In gateway/combined mode (or whenever objects carry bindings) a southbound
    transport is started from ``transport_uri``.
    """
    from bbc_sim.models import RuntimeMode

    app = build_application(config)
    manager = None
    has_bindings = any(o.binding for o in config.objects)
    needs_southbound = config.mode is not RuntimeMode.simulator and has_bindings
    if needs_southbound and not transport_uri:
        _log.warning(
            "mode=%s with bound object(s) but no --transport; southbound bindings are "
            "inactive (use memory:// for an in-process fake)", config.mode.value,
        )
    if needs_southbound and transport_uri:
        from bbc_sim.southbound.binding import SouthboundManager
        from bbc_sim.southbound.factory import make_transport

        manager = SouthboundManager(app, config, make_transport(transport_uri))
        await manager.start()

    stop = stop or asyncio.Event()
    try:
        await stop.wait()
    finally:
        if manager is not None:
            await manager.stop()
        app.close()


def run(config: SimulatorConfig, transport_uri: str | None = None) -> None:
    """Blocking entry point for the CLI."""
    asyncio.run(run_async(config, transport_uri=transport_uri))


def run_from_path(config_path: str | Path, transport_uri: str | None = None) -> None:
    run(load_config(config_path), transport_uri=transport_uri)
