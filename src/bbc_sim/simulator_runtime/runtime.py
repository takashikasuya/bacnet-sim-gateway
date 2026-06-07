"""Assemble and run a full B-BC: BACnet/IP server + simulation engine + southbound
binding + optional REST control plane (ADR-010 single loop).

This is the single place that wires the EP-001..007 components together so `bbc-sim run`
actually drives values, serves bindings, and exposes the control plane and admin UI.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from bbc_sim.models import RuntimeMode, SimulatorConfig
from bbc_sim.simulation.engine import SimulationEngine
from bbc_sim.simulation.fault import FaultController
from bbc_sim.simulator_runtime.app import BBCApplication, build_application

_log = logging.getLogger(__name__)


class Runtime:
    """Owns the application and its subsystems for the lifetime of a run."""

    def __init__(
        self,
        config: SimulatorConfig,
        *,
        transport_uri: str | None = None,
        rest_port: int | None = None,
        tick_seconds: float = 1.0,
        with_network: bool = True,
        source_path: Path | None = None,
        ui_enabled: bool = False,
    ) -> None:
        self.config = config
        self.transport_uri = transport_uri
        self.rest_port = rest_port
        self.source_path = source_path
        self.ui_enabled = ui_enabled
        self.with_network = with_network  # northbound BACnet/IP datalink is live
        self.faults = FaultController()
        self.app: BBCApplication = build_application(config, with_network=with_network)

        # Simulation engine drives internally-generated values (simulator/combined).
        self.engine: SimulationEngine | None = None
        if config.mode in (RuntimeMode.simulator, RuntimeMode.combined):
            engine = SimulationEngine(self.app, config, self.faults, tick_seconds)
            if engine.has_generators():  # only run if something is actually generated
                self.engine = engine

        self.manager: Any = None  # SouthboundManager (gateway/combined)
        self._rest_server: Any = None  # uvicorn.Server
        self._rest_task: asyncio.Task[None] | None = None

        # Observability: ring-buffer log handler (EP-007.1)
        from bbc_sim.observability.log_buffer import RingBufferLogHandler

        self._log_handler = RingBufferLogHandler(capacity=1000)
        logging.getLogger("bbc_sim").addHandler(self._log_handler)

    async def start(self) -> None:
        if self.engine is not None:
            await self.engine.start()

        needs_southbound = self.config.mode is not RuntimeMode.simulator and any(
            o.binding for o in self.config.objects
        )
        if needs_southbound and not self.transport_uri:
            _log.warning(
                "mode=%s with bound object(s) but no transport_uri; southbound bindings "
                "are inactive (use memory:// for an in-process fake)",
                self.config.mode.value,
            )
        if needs_southbound and self.transport_uri:
            from bbc_sim.southbound.binding import SouthboundManager
            from bbc_sim.southbound.factory import make_transport

            self.manager = SouthboundManager(
                self.app, self.config, make_transport(self.transport_uri)
            )
            await self.manager.start()

        if self.rest_port is not None:
            import uvicorn

            from bbc_sim.rest.api import create_app
            from bbc_sim.rest.reload import PointListReloader
            from bbc_sim.rest.status import StatusProvider

            status = StatusProvider(
                config=self.config,
                app=self.app,
                bound=self.with_network,  # reflect the actual BACnet/IP bind state
                get_manager=lambda: self.manager,
                log_handler=self._log_handler,
            )
            reloader = PointListReloader(source_path=self.source_path, runtime=self)
            api = create_app(
                self.app,
                self.config,
                self.faults,
                status=status,
                reloader=reloader,
                ui_enabled=self.ui_enabled,
            )
            uv_config = uvicorn.Config(
                api, host="127.0.0.1", port=self.rest_port, log_level="warning"
            )
            self._rest_server = uvicorn.Server(uv_config)
            self._rest_task = asyncio.create_task(self._rest_server.serve())

    async def stop(self) -> None:
        if self.engine is not None:
            await self.engine.stop()
        if self.manager is not None:
            await self.manager.stop()
        if self._rest_server is not None:
            self._rest_server.should_exit = True
        if self._rest_task is not None:
            await asyncio.gather(self._rest_task, return_exceptions=True)
        self.app.close()
        logging.getLogger("bbc_sim").removeHandler(self._log_handler)

    async def run_forever(self, stop: asyncio.Event | None = None) -> None:
        stop = stop or asyncio.Event()
        await self.start()
        try:
            await stop.wait()
        finally:
            await self.stop()
