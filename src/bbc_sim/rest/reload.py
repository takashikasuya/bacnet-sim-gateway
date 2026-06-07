"""Point-list reload for a running B-BC (EP-007.4, PR-F-056).

Strategy: validate → diff → apply-or-defer.  Structural changes (object_type,
object_instance, bbc.device_id, network bind) require restart to avoid datalink churn
(ADR-010).  Non-structural changes (writable, description, tags, update/generators,
metadata) are applied live.  bbc_id is never re-derived from gateway_id (ADR-003).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bbc_sim.models import BacnetObjectSpec, SimulatorConfig
from bbc_sim.yaml_generator.yaml_io import load_config, validate_config

if TYPE_CHECKING:
    from bbc_sim.simulator_runtime.runtime import Runtime


@dataclass
class ReloadDiff:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    modified_live: list[str] = field(default_factory=list)
    modified_restart: list[str] = field(default_factory=list)


def _is_structural(old: BacnetObjectSpec, new: BacnetObjectSpec) -> bool:
    return old.object_type != new.object_type or old.object_instance != new.object_instance


def _needs_live_update(old: BacnetObjectSpec, new: BacnetObjectSpec) -> bool:
    return (
        old.writable != new.writable
        or old.description != new.description
        or old.tags != new.tags
        or old.metadata != new.metadata
        or old.update != new.update
    )


def _compute_diff(old_cfg: SimulatorConfig, new_cfg: SimulatorConfig) -> tuple[ReloadDiff, bool]:
    old_map = {s.point_id: s for s in old_cfg.objects}
    new_map = {s.point_id: s for s in new_cfg.objects}
    diff = ReloadDiff()
    for pid in sorted(set(new_map) - set(old_map)):
        diff.added.append(pid)
    for pid in sorted(set(old_map) - set(new_map)):
        diff.removed.append(pid)
    for pid in sorted(set(old_map) & set(new_map)):
        if _is_structural(old_map[pid], new_map[pid]):
            diff.modified_restart.append(pid)
        elif _needs_live_update(old_map[pid], new_map[pid]):
            diff.modified_live.append(pid)
    structural_cfg = (
        old_cfg.bbc.device_id != new_cfg.bbc.device_id
        or old_cfg.network.bind_address != new_cfg.network.bind_address
        or old_cfg.network.port != new_cfg.network.port
    )
    needs_restart = bool(diff.modified_restart) or structural_cfg
    return diff, needs_restart


class PointListReloader:
    def __init__(self, source_path: Path | None, runtime: Runtime) -> None:
        self._source = source_path
        self._runtime = runtime
        self.last_reload_ts: float | None = None
        self.last_result: str | None = None

    def apply(self) -> dict[str, Any]:
        if self._source is None:
            return {
                "status": "no_source",
                "diff": None,
                "errors": ["no source path; start bbc-sim run with --source-path"],
            }
        try:
            new_cfg = load_config(self._source)
        except Exception as exc:
            self.last_result = "read_error"
            return {"status": "read_error", "diff": None, "errors": [str(exc)]}

        # Preserve running identity — never re-derive bbc_id from gateway_id (ADR-003)
        new_cfg.bbc.bbc_id = self._runtime.config.bbc.bbc_id

        errors = validate_config(new_cfg)
        if errors:
            self.last_result = "validation_failed"
            return {"status": "validation_failed", "diff": None, "errors": errors}

        diff, needs_restart = _compute_diff(self._runtime.config, new_cfg)
        self.last_reload_ts = time.time()

        if needs_restart:
            self.last_result = "restart_required"
            return {
                "status": "restart_required",
                "diff": _diff_dict(diff),
                "errors": [],
                "hint": (
                    f"bbc-sim run -c {self._source} "
                    f"--mode {self._runtime.config.mode.value}"
                ),
            }

        _apply_live(self._runtime, new_cfg, diff)
        self.last_result = "applied"
        return {"status": "applied", "diff": _diff_dict(diff), "errors": []}

    def info(self) -> dict[str, Any]:
        return {
            "source_path": str(self._source) if self._source else None,
            "object_count": len(self._runtime.config.objects),
            "last_reload_ts": self.last_reload_ts,
            "last_result": self.last_result,
        }


def _diff_dict(diff: ReloadDiff) -> dict[str, Any]:
    return {
        "added": diff.added,
        "removed": diff.removed,
        "modified_live": diff.modified_live,
        "modified_restart": diff.modified_restart,
    }


def _apply_live(runtime: Runtime, new_cfg: SimulatorConfig, diff: ReloadDiff) -> None:
    from bacpypes3.primitivedata import ObjectIdentifier

    from bbc_sim.bacnet_objects.builder import _OID_TYPE, build_object
    from bbc_sim.simulator_runtime.app import compute_writable_oids

    app = runtime.app
    old_map = {s.point_id: s for s in runtime.config.objects}
    new_map = {s.point_id: s for s in new_cfg.objects}

    for pid in diff.removed:
        spec = old_map[pid]
        oid = ObjectIdentifier((_OID_TYPE[spec.object_type], spec.object_instance))
        obj = app.get_object_id(oid)
        if obj is not None:
            app.delete_object(obj)

    for pid in diff.added:
        app.add_object(build_object(new_map[pid]))

    for pid in diff.modified_live:
        spec = new_map[pid]
        oid = ObjectIdentifier((_OID_TYPE[spec.object_type], spec.object_instance))
        obj = app.get_object_id(oid)
        if obj is None:
            continue
        obj.description = spec.description

    # Rebuild writable OID set from new objects
    app._writable_oids = compute_writable_oids(new_cfg)

    # Rebuild simulation generators for the new object set
    if runtime.engine is not None:
        runtime.engine.rebuild(new_cfg)

    # Update config in-place so existing REST handlers see new objects
    runtime.config.objects = new_cfg.objects
