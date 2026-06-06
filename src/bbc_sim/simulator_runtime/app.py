"""Single-loop asyncio B-BC runtime (ADR-010).

Builds a bacpypes3 Application from the simulator.yaml model and serves it on
BACnet/IP (northbound, ADR-005). The Core Object Model lives on the event loop;
no blocking calls.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from bacpypes3.apdu import WritePropertyRequest
from bacpypes3.app import Application
from bacpypes3.errors import ExecutionError

from bbc_sim.bacnet_objects.builder import build_object_list
from bbc_sim.models import SimulatorConfig
from bbc_sim.yaml_generator.yaml_io import load_config

_PRESENT_VALUE = {"present-value", "presentValue"}


class BBCApplication(Application):
    """Application that enforces SBCO `writable` on present-value (AC-5).

    Only points marked writable (Value/Output) accept WriteProperty on
    present-value; Inputs reject with writeAccessDenied.
    """

    _writable_oids: frozenset[tuple[str, int]] = frozenset()

    async def do_WritePropertyRequest(self, apdu: WritePropertyRequest) -> None:
        prop = str(apdu.propertyIdentifier)
        oid = (str(apdu.objectIdentifier[0]), int(apdu.objectIdentifier[1]))
        if prop in _PRESENT_VALUE and oid not in self._writable_oids:
            raise ExecutionError(errorClass="property", errorCode="writeAccessDenied")
        await super().do_WritePropertyRequest(apdu)


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


async def run_async(config: SimulatorConfig, stop: asyncio.Event | None = None) -> None:
    """Run the B-BC until ``stop`` is set (or forever)."""
    app = build_application(config)
    stop = stop or asyncio.Event()
    try:
        await stop.wait()
    finally:
        app.close()


def run(config: SimulatorConfig) -> None:
    """Blocking entry point for the CLI."""
    asyncio.run(run_async(config))


def run_from_path(config_path: str | Path) -> None:
    run(load_config(config_path))
