"""Serialize/deserialize and validate the simulator.yaml intermediate model.

simulator.yaml is the single intermediate shared by all modes (ADR-004). The schema
follows requirements §14.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from bbc_sim.models import (
    BacnetObjectSpec,
    BacnetObjectType,
    BbcConfig,
    BindingDirection,
    BindingMapping,
    BindingSpec,
    MultiDeviceConfig,
    NetworkConfig,
    RuntimeMode,
    SimulatorConfig,
    UpdateConfig,
)


def _object_to_dict(o: BacnetObjectSpec) -> dict[str, Any]:
    d: dict[str, Any] = {
        "point_id": o.point_id,
        "object_type": o.object_type.value,
        "object_instance": o.object_instance,
        "object_name": o.object_name,
        "present_value": o.present_value,
        "writable": o.writable,
        "scale": o.scale,
    }
    if o.units is not None:
        d["units"] = o.units
    if o.min_pres_value is not None:
        d["min_pres_value"] = o.min_pres_value
    if o.max_pres_value is not None:
        d["max_pres_value"] = o.max_pres_value
    if o.state_text:
        d["state_text"] = o.state_text
    if o.active_text is not None:
        d["active_text"] = o.active_text
    if o.inactive_text is not None:
        d["inactive_text"] = o.inactive_text
    if o.description:
        d["description"] = o.description
    if o.update.interval is not None or o.update.mode is not None or o.update.params:
        upd: dict[str, Any] = {}
        if o.update.interval is not None:
            upd["interval"] = o.update.interval
        if o.update.mode is not None:
            upd["mode"] = o.update.mode
        if o.update.params:
            upd["params"] = o.update.params
        d["update"] = upd
    if o.tags:
        d["tags"] = o.tags
    if o.metadata:
        d["metadata"] = o.metadata
    if o.binding is not None:
        b: dict[str, Any] = {
            "protocol": o.binding.protocol,
            "direction": o.binding.direction.value,
        }
        if o.binding.address is not None:
            b["address"] = o.binding.address
        m = o.binding.mapping
        mapping: dict[str, Any] = {"type": m.type, "scale": m.scale, "offset": m.offset}
        if m.value_path is not None:
            mapping["value_path"] = m.value_path
        if m.enum_map:
            mapping["enum_map"] = m.enum_map
        b["mapping"] = mapping
        d["binding"] = b
    return d


def _network_to_dict(net: NetworkConfig) -> dict[str, Any]:
    d: dict[str, Any] = {
        "type": net.type,
        "bind_address": net.bind_address,
        "port": net.port,
    }
    if net.foreign_bbmd:
        d["foreign_bbmd"] = net.foreign_bbmd
        d["foreign_ttl"] = net.foreign_ttl
    if net.bbmd_bdt:
        d["bbmd_bdt"] = net.bbmd_bdt
    return d


def config_to_dict(config: SimulatorConfig) -> dict[str, Any]:
    return {
        "bbc": {
            "bbc_id": config.bbc.bbc_id,
            "device_id": config.bbc.device_id,
            "object_name": config.bbc.object_name,
            "vendor_name": config.bbc.vendor_name,
            "vendor_identifier": config.bbc.vendor_identifier,
            "model_name": config.bbc.model_name,
        },
        "network": _network_to_dict(config.network),
        "mode": config.mode.value,
        "objects": [_object_to_dict(o) for o in config.objects],
    }


def dump_config(config: SimulatorConfig, path: str | Path) -> None:
    Path(path).write_text(
        yaml.safe_dump(config_to_dict(config), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _coerce_bool(value: Any) -> bool:
    """Interpret YAML/JSON truthiness, including quoted strings like 'false'/'no'."""
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "y", "on")
    return bool(value)


def _binding_from_dict(b: dict[str, Any] | None) -> BindingSpec | None:
    if not b:
        return None
    m = b.get("mapping") or {}
    return BindingSpec(
        protocol=b["protocol"],
        direction=BindingDirection(b.get("direction", "telemetry")),
        address=b.get("address"),
        mapping=BindingMapping(
            type=m.get("type", "real"),
            scale=float(m.get("scale", 1.0)),
            offset=float(m.get("offset", 0.0)),
            value_path=m.get("value_path"),
            enum_map=dict(m.get("enum_map", {})),
        ),
    )


def _object_from_dict(d: dict[str, Any]) -> BacnetObjectSpec:
    upd = d.get("update") or {}
    return BacnetObjectSpec(
        point_id=d["point_id"],
        object_type=BacnetObjectType(d["object_type"]),
        object_instance=int(d["object_instance"]),
        object_name=d["object_name"],
        present_value=d.get("present_value"),
        units=d.get("units"),
        min_pres_value=d.get("min_pres_value"),
        max_pres_value=d.get("max_pres_value"),
        state_text=list(d.get("state_text", [])),
        active_text=d.get("active_text"),
        inactive_text=d.get("inactive_text"),
        scale=float(d.get("scale", 1.0)),
        writable=_coerce_bool(d.get("writable", False)),
        description=d.get("description", ""),
        update=UpdateConfig(
            interval=upd.get("interval"),
            mode=upd.get("mode"),
            params=dict(upd.get("params") or {}),  # tolerate `params: null`
        ),
        metadata=dict(d.get("metadata", {})),
        binding=_binding_from_dict(d.get("binding")),
        tags=list(d.get("tags", [])),
    )


def dict_to_config(d: dict[str, Any]) -> SimulatorConfig:
    bbc = d["bbc"]
    net = d.get("network", {})
    return SimulatorConfig(
        bbc=BbcConfig(
            bbc_id=bbc["bbc_id"],
            device_id=int(bbc["device_id"]),
            object_name=bbc.get("object_name", "Local Virtual B-BC"),
            vendor_name=bbc.get("vendor_name", "SBCO Simulator"),
            vendor_identifier=int(bbc.get("vendor_identifier", 999)),
            model_name=bbc.get("model_name", "Virtual BBC"),
        ),
        network=NetworkConfig(
            type=net.get("type", "bacnet-ip"),
            bind_address=net.get("bind_address", "0.0.0.0"),
            port=int(net.get("port", 47808)),
            foreign_bbmd=net.get("foreign_bbmd"),
            foreign_ttl=int(net.get("foreign_ttl") or 30),  # tolerate explicit null
            bbmd_bdt=list(net.get("bbmd_bdt") or []),
        ),
        objects=[_object_from_dict(o) for o in d.get("objects", [])],
        mode=RuntimeMode(d.get("mode", "simulator")),
    )


def load_config(path: str | Path) -> SimulatorConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "devices" in data:
        raise ValueError(
            f"{path} is a multi-device YAML (device_mapping: multi-device). "
            "The runtime currently supports single-device configs only. "
            "Re-generate without --device-mapping multi-device, or select one "
            "device's section manually."
        )
    return dict_to_config(data)


def validate_config(config: SimulatorConfig) -> list[str]:
    """Validate a SimulatorConfig; returns human-readable errors (empty == valid)."""
    errors: list[str] = []
    if config.bbc.device_id <= 0:
        errors.append("bbc.device_id must be positive")

    seen_instances: dict[BacnetObjectType, set[int]] = defaultdict(set)
    seen_points: set[str] = set()
    for o in config.objects:
        if o.point_id in seen_points:
            errors.append(f"duplicate point_id: {o.point_id}")
        seen_points.add(o.point_id)
        s = seen_instances[o.object_type]
        if o.object_instance in s:
            errors.append(f"duplicate object instance {o.object_type.value}:{o.object_instance}")
        s.add(o.object_instance)
        if o.object_type.is_multistate and not o.state_text:
            errors.append(f"{o.point_id}: multi-state object missing state_text")
        if (
            o.binding
            and o.binding.direction in (BindingDirection.command, BindingDirection.both)
            and not o.writable
        ):
            errors.append(
                f"{o.point_id}: command binding requires writable=true "
                "(non-writable objects reject WriteProperty)"
            )
    return errors


def validate_yaml(path: str | Path) -> list[str]:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"invalid simulator.yaml: {exc}"]
    try:
        if "devices" in data:
            return validate_multi_device_config(load_multi_device_config(path))
        return validate_config(dict_to_config(data))
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        return [f"invalid simulator.yaml: {exc}"]


# ---------------------------------------------------------------------------
# Multi-device YAML (ADR-011 multi-device mode)
# ---------------------------------------------------------------------------


def dump_multi_device_config(config: MultiDeviceConfig, path: str | Path) -> None:
    data = {
        "device_mapping": config.device_mapping.value,
        "devices": [config_to_dict(d) for d in config.devices],
    }
    Path(path).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def load_multi_device_config(path: str | Path) -> MultiDeviceConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return MultiDeviceConfig(
        devices=[dict_to_config(d) for d in (data.get("devices") or [])],
    )


def validate_multi_device_config(config: MultiDeviceConfig) -> list[str]:
    """Validate each device independently; cross-device instance reuse is allowed."""
    errors: list[str] = []
    seen_device_ids: set[int] = set()
    for i, dev in enumerate(config.devices):
        if dev.bbc.device_id in seen_device_ids:
            errors.append(
                f"device[{i}] ({dev.bbc.bbc_id}): duplicate device_id {dev.bbc.device_id}"
            )
        seen_device_ids.add(dev.bbc.device_id)
        for e in validate_config(dev):
            errors.append(f"device[{i}] ({dev.bbc.bbc_id}): {e}")
    return errors
