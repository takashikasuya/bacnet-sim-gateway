"""Simulation drive engine (ADR-010: single-loop asyncio).

Ticks per-object value generators and writes presentValue on the Core Object Model,
skipping objects suppressed by an active fault (freeze / comm-loss).
"""

from __future__ import annotations

import asyncio
from typing import Any

from bacpypes3.app import Application
from bacpypes3.primitivedata import ObjectIdentifier

from bbc_sim.bacnet_objects.builder import _OID_TYPE
from bbc_sim.models import BacnetObjectSpec, SimulatorConfig
from bbc_sim.simulation.fault import FaultController
from bbc_sim.simulation.generators import ValueGenerator, make_generator


def _coerce(spec: BacnetObjectSpec, value: Any) -> Any:
    if spec.object_type.is_binary:
        truthy = str(value).lower() in ("1", "true", "on", "active", "yes")
        return "active" if truthy else "inactive"
    if spec.object_type.is_multistate:
        return int(value)
    return float(value)


class SimulationEngine:
    """Drive simulated values for objects that declare an update mode."""

    def __init__(
        self,
        app: Application,
        config: SimulatorConfig,
        fault_controller: FaultController | None = None,
        tick_seconds: float = 1.0,
    ) -> None:
        self.app = app
        self.config = config
        self.faults = fault_controller or FaultController()
        self.tick_seconds = tick_seconds
        self._generators: list[tuple[BacnetObjectSpec, ObjectIdentifier, ValueGenerator]] = []
        for spec in config.objects:
            gen = make_generator(spec)
            if gen is not None:
                oid = ObjectIdentifier((_OID_TYPE[spec.object_type], spec.object_instance))
                self._generators.append((spec, oid, gen))
        self._task: asyncio.Task[None] | None = None

    def has_generators(self) -> bool:
        """Whether any object declares a value-generation mode."""
        return bool(self._generators)

    def tick(self, t: float) -> None:
        """Advance all generators to time ``t`` and write presentValue (testable)."""
        for spec, oid, gen in self._generators:
            obj = self.app.get_object_id(oid)
            if obj is None or self.faults.is_suppressed(obj):
                continue
            obj.presentValue = _coerce(spec, gen.next(t))

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

    async def _loop(self) -> None:
        t = 0.0
        while True:
            self.tick(t)
            await asyncio.sleep(self.tick_seconds)
            t += self.tick_seconds
