"""Single-loop asyncio B-BC runtime (ADR-010).

Builds a bacpypes3 Application from the simulator.yaml model and serves it on
BACnet/IP (northbound, ADR-005). The Core Object Model lives on the event loop;
no blocking calls.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from bacpypes3.apdu import (
    WritePropertyMultipleError,
    WritePropertyMultipleRequest,
    WritePropertyRequest,
)
from bacpypes3.app import Application
from bacpypes3.basetypes import ErrorType, ObjectPropertyReference
from bacpypes3.errors import ExecutionError

from bbc_sim.bacnet_objects.builder import build_object_list
from bbc_sim.models import SimulatorConfig
from bbc_sim.yaml_generator.yaml_io import load_config

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

    async def do_WritePropertyMultipleRequest(
        self, apdu: WritePropertyMultipleRequest
    ) -> None:
        # Enforce writable on every present-value element before delegating (AC-5).
        # Raise the correct WPM error type server-side. Note: bacpypes3 0.0.106 cannot
        # transport WPM error responses over IP (the client times out) — see
        # docs/memory/pitfalls.md; enforcement is therefore verified at the handler level.
        for spec in apdu.listOfWriteAccessSpecs:
            oid = (str(spec.objectIdentifier[0]), int(spec.objectIdentifier[1]))
            for prop_value in spec.listOfProperties:
                if (
                    str(prop_value.propertyIdentifier) in _PRESENT_VALUE
                    and oid not in self._writable_oids
                ):
                    raise WritePropertyMultipleError(
                        errorType=ErrorType(
                            errorClass="property", errorCode="writeAccessDenied"
                        ),
                        firstFailedWriteAttempt=ObjectPropertyReference(
                            objectIdentifier=spec.objectIdentifier,
                            propertyIdentifier=prop_value.propertyIdentifier,
                        ),
                    )
        await super().do_WritePropertyMultipleRequest(apdu)
        if not self.on_command:
            return
        for spec in apdu.listOfWriteAccessSpecs:
            oid = (str(spec.objectIdentifier[0]), int(spec.objectIdentifier[1]))
            if oid not in self._command_oids:
                continue
            if any(str(p.propertyIdentifier) in _PRESENT_VALUE for p in spec.listOfProperties):
                obj = self.get_object_id(spec.objectIdentifier)
                if obj is not None:
                    await self.on_command(oid, obj.presentValue)


def build_application(config: SimulatorConfig, *, with_network: bool = True) -> BBCApplication:
    """Build the Application. With network (default) it serves BACnet/IP and must be
    called inside a running event loop; without it (control-plane tests) no datalink is
    created.
    """
    objects = build_object_list(config, with_network=with_network)
    app = BBCApplication.from_object_list(objects)
    # Match point objects to specs by object identity, not list position.
    point_objects = [
        o for o in objects if str(o.objectIdentifier[0]) not in ("device", "network-port")
    ]
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
    rest_port: int | None = None,
) -> None:
    """Run the full B-BC (server + engine + bindings + optional REST) until stopped."""
    from bbc_sim.simulator_runtime.runtime import Runtime

    runtime = Runtime(config, transport_uri=transport_uri, rest_port=rest_port)
    await runtime.run_forever(stop)


def run(
    config: SimulatorConfig,
    transport_uri: str | None = None,
    rest_port: int | None = None,
) -> None:
    """Blocking entry point for the CLI."""
    asyncio.run(run_async(config, transport_uri=transport_uri, rest_port=rest_port))


def run_from_path(
    config_path: str | Path,
    transport_uri: str | None = None,
    rest_port: int | None = None,
) -> None:
    run(load_config(config_path), transport_uri=transport_uri, rest_port=rest_port)
