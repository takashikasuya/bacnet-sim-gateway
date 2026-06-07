"""Single-loop asyncio B-BC runtime (ADR-010).

Builds a bacpypes3 Application from the simulator.yaml model and serves it on
BACnet/IP (northbound, ADR-005). The Core Object Model lives on the event loop;
no blocking calls.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
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

from bbc_sim.bacnet_objects.builder import build_object_list, oid_key
from bbc_sim.models import SimulatorConfig
from bbc_sim.yaml_generator.yaml_io import load_config

_PRESENT_VALUE = {"present-value", "presentValue"}

CommandHook = Callable[[tuple[str, int], Any], Awaitable[None]]


@dataclass
class Counters:
    """Northbound BACnet request counters (non-blocking int increments, ADR-010)."""

    who_is: int = field(default=0)
    i_am_sent: int = field(default=0)
    read_property: int = field(default=0)
    read_property_multiple: int = field(default=0)
    write_property: int = field(default=0)
    write_property_multiple: int = field(default=0)
    write_access_denied: int = field(default=0)


def compute_writable_oids(config: SimulatorConfig) -> frozenset[tuple[str, int]]:
    """Derive the writable-OID frozenset from config (used by build_application and reload)."""
    return frozenset(oid_key(spec) for spec in config.objects if spec.writable)


class BBCApplication(Application):
    """Application that enforces SBCO `writable` on present-value (AC-5).

    Only points marked writable (Value/Output) accept WriteProperty on
    present-value; Inputs reject with writeAccessDenied. A command hook lets the
    southbound manager forward writes to bound objects (command path).
    """

    _writable_oids: frozenset[tuple[str, int]] = frozenset()
    _command_oids: frozenset[tuple[str, int]] = frozenset()
    on_command: CommandHook | None = None
    counters: Counters  # set by build_application

    # --- configuration accessors (keep callers off private attributes) ---

    def set_writable_oids(self, oids: frozenset[tuple[str, int]]) -> None:
        """Set the OIDs whose present-value accepts WriteProperty (AC-5)."""
        self._writable_oids = oids

    def set_command_oids(self, oids: frozenset[tuple[str, int]]) -> None:
        """Set the OIDs that forward northbound writes to the command hook."""
        self._command_oids = oids

    def set_command_hook(self, hook: CommandHook | None) -> None:
        """Register (or clear) the southbound command-forwarding hook."""
        self.on_command = hook

    async def do_WhoIsRequest(self, apdu: Any) -> None:  # type: ignore[override]
        self.counters.who_is += 1
        await super().do_WhoIsRequest(apdu)  # type: ignore[misc]

    async def do_ReadPropertyRequest(self, apdu: Any) -> None:  # type: ignore[override]
        self.counters.read_property += 1
        await super().do_ReadPropertyRequest(apdu)  # type: ignore[misc]

    async def do_ReadPropertyMultipleRequest(self, apdu: Any) -> None:  # type: ignore[override]
        self.counters.read_property_multiple += 1
        await super().do_ReadPropertyMultipleRequest(apdu)  # type: ignore[misc]

    async def do_WritePropertyRequest(self, apdu: WritePropertyRequest) -> None:
        prop = str(apdu.propertyIdentifier)
        oid = (str(apdu.objectIdentifier[0]), int(apdu.objectIdentifier[1]))
        if prop in _PRESENT_VALUE and oid not in self._writable_oids:
            self.counters.write_access_denied += 1
            raise ExecutionError(errorClass="property", errorCode="writeAccessDenied")
        self.counters.write_property += 1
        await super().do_WritePropertyRequest(apdu)
        if prop in _PRESENT_VALUE and self.on_command and oid in self._command_oids:
            obj = self.get_object_id(apdu.objectIdentifier)
            if obj is not None:
                await self.on_command(oid, obj.presentValue)

    async def do_WritePropertyMultipleRequest(self, apdu: WritePropertyMultipleRequest) -> None:
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
                        errorType=ErrorType(errorClass="property", errorCode="writeAccessDenied"),
                        firstFailedWriteAttempt=ObjectPropertyReference(
                            objectIdentifier=spec.objectIdentifier,
                            propertyIdentifier=prop_value.propertyIdentifier,
                        ),
                    )
        self.counters.write_property_multiple += 1
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
    app.counters = Counters()
    app.set_writable_oids(compute_writable_oids(config))
    return app


async def run_async(
    config: SimulatorConfig,
    stop: asyncio.Event | None = None,
    transport_uri: str | None = None,
    rest_port: int | None = None,
    source_path: Path | None = None,
    ui_enabled: bool = False,
) -> None:
    """Run the full B-BC (server + engine + bindings + optional REST) until stopped."""
    from bbc_sim.simulator_runtime.runtime import Runtime

    runtime = Runtime(
        config,
        transport_uri=transport_uri,
        rest_port=rest_port,
        source_path=source_path,
        ui_enabled=ui_enabled,
    )
    await runtime.run_forever(stop)


def run(
    config: SimulatorConfig,
    transport_uri: str | None = None,
    rest_port: int | None = None,
    source_path: Path | None = None,
    ui_enabled: bool = False,
) -> None:
    """Blocking entry point for the CLI."""
    asyncio.run(
        run_async(
            config,
            transport_uri=transport_uri,
            rest_port=rest_port,
            source_path=source_path,
            ui_enabled=ui_enabled,
        )
    )


def run_from_path(
    config_path: str | Path,
    transport_uri: str | None = None,
    rest_port: int | None = None,
) -> None:
    p = Path(config_path)
    run(load_config(p), transport_uri=transport_uri, rest_port=rest_port, source_path=p.resolve())
