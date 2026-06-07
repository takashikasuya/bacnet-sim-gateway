"""StatusProvider — aggregates live runtime state for /status/* REST endpoints and UI.

Holds references to live objects.  SouthboundManager is created lazily in
Runtime.start(), so it must be accessed via get_manager() callable rather than
a snapshot taken at construction.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bbc_sim.models import SimulatorConfig

if TYPE_CHECKING:
    from bbc_sim.observability.log_buffer import RingBufferLogHandler
    from bbc_sim.simulator_runtime.app import BBCApplication
    from bbc_sim.southbound.binding import SouthboundManager


@dataclass
class StatusProvider:
    config: SimulatorConfig
    app: BBCApplication
    bound: bool  # True when BACnet/IP datalink is live (with_network=True)
    get_manager: Callable[[], SouthboundManager | None]
    log_handler: RingBufferLogHandler | None = None
    _start_ts: float = field(default_factory=time.time, init=False)

    def runtime_status(self) -> dict[str, Any]:
        cfg = self.config
        manager = self.get_manager()
        counters = getattr(self.app, "counters", None)
        return {
            "mode": cfg.mode.value,
            "bound": self.bound,
            "uptime_seconds": round(time.time() - self._start_ts, 1),
            "network": {
                "bind_address": cfg.network.bind_address,
                "port": cfg.network.port,
                "foreign_bbmd": cfg.network.foreign_bbmd,
                "bbmd_bdt": cfg.network.bbmd_bdt,
            },
            "device": {
                "device_id": cfg.bbc.device_id,
                "bbc_id": cfg.bbc.bbc_id,
                "object_name": cfg.bbc.object_name,
            },
            "object_count": len(cfg.objects),
            "northbound_counters": _counters_dict(counters),
            "southbound_active": manager is not None,
        }

    def northbound_status(self) -> dict[str, Any]:
        cfg = self.config
        counters = getattr(self.app, "counters", None)
        return {
            "bound": self.bound,
            "bind_address": cfg.network.bind_address,
            "port": cfg.network.port,
            "bbmd": {
                "enabled": bool(cfg.network.bbmd_bdt),
                "bdt": cfg.network.bbmd_bdt,
            },
            "foreign_device": {
                "registered": cfg.network.foreign_bbmd is not None,
                "bbmd": cfg.network.foreign_bbmd,
                "ttl": cfg.network.foreign_ttl,
            },
            "counters": _counters_dict(counters),
        }

    def southbound_status(self) -> dict[str, Any]:
        manager = self.get_manager()
        if manager is None:
            return {"active": False, "protocols": [], "points": []}
        return manager.status()


def _counters_dict(counters: Any) -> dict[str, int]:
    if counters is None:
        return {k: 0 for k in (
            "who_is", "i_am_sent", "read_property", "read_property_multiple",
            "write_property", "write_property_multiple", "write_access_denied",
        )}
    return {
        "who_is": counters.who_is,
        "i_am_sent": counters.i_am_sent,
        "read_property": counters.read_property,
        "read_property_multiple": counters.read_property_multiple,
        "write_property": counters.write_property,
        "write_property_multiple": counters.write_property_multiple,
        "write_access_denied": counters.write_access_denied,
    }
