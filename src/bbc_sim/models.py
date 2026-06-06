"""Domain model: SBCO point list rows and the simulator.yaml intermediate model.

The YAML model is the single intermediate shared by all modes (ADR-004).
`gateway_id` is metadata only and must never become the BACnet device id (ADR-003).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# Required input columns (requirements §5).
REQUIRED_COLUMNS: tuple[str, ...] = (
    "gateway_id",
    "point_id",
    "point_name",
    "point_type",
    "point_specification",
    "writable",
    "device_id",
    "device_name",
    "device_type",
    "site",
    "building",
    "floor",
    "installation_area",
    "local_id",
)

LABEL_SEP = "&&"


class PointListError(Exception):
    """Raised when an SBCO point list cannot be read (structural error)."""


class RuntimeMode(StrEnum):
    """Value-source mode (operating-modes.md). Orthogonal to device-mapping mode."""

    simulator = "simulator"  # values internally generated
    gateway = "gateway"      # values sourced from southbound bindings
    combined = "combined"    # per-object: simulate or bind


class BindingDirection(StrEnum):
    telemetry = "telemetry"  # south -> BACnet presentValue
    command = "command"      # north WriteProperty -> south
    both = "both"


class BacnetObjectType(StrEnum):
    """BACnet object types used by this simulator, with ASHRAE 135 enum values."""

    analogInput = "analogInput"
    analogOutput = "analogOutput"
    analogValue = "analogValue"
    binaryInput = "binaryInput"
    binaryOutput = "binaryOutput"
    binaryValue = "binaryValue"
    multiStateInput = "multiStateInput"
    multiStateOutput = "multiStateOutput"
    multiStateValue = "multiStateValue"

    @property
    def is_analog(self) -> bool:
        return self in (
            BacnetObjectType.analogInput,
            BacnetObjectType.analogOutput,
            BacnetObjectType.analogValue,
        )

    @property
    def is_binary(self) -> bool:
        return self in (
            BacnetObjectType.binaryInput,
            BacnetObjectType.binaryOutput,
            BacnetObjectType.binaryValue,
        )

    @property
    def is_multistate(self) -> bool:
        return self in (
            BacnetObjectType.multiStateInput,
            BacnetObjectType.multiStateOutput,
            BacnetObjectType.multiStateValue,
        )


@dataclass
class SbcoPoint:
    """One normalized row of an SBCO standard point list."""

    gateway_id: str
    device_id: str
    device_name: str
    device_type: str
    site: str
    building: str
    floor: str
    installation_area: str
    target_area: str
    panel: str
    point_type: str
    point_specification: str
    point_id: str
    point_name: str
    writable: bool
    interval: int | None
    unit: str
    max_pres_value: float | None
    min_pres_value: float | None
    labels: list[str]
    scale: float
    tags: list[str]
    supplier: str
    owner: str
    description: str
    local_id: str
    device_id_bacnet: str
    instance_no_bacnet: int | None
    object_type_bacnet: str


# ---- simulator.yaml intermediate model (requirements §14, ADR-004) ----


@dataclass
class BbcConfig:
    bbc_id: str
    device_id: int
    object_name: str = "Local Virtual B-BC"
    vendor_name: str = "SBCO Simulator"
    vendor_identifier: int = 999
    model_name: str = "Virtual BBC"


@dataclass
class NetworkConfig:
    type: str = "bacnet-ip"
    bind_address: str = "0.0.0.0"
    port: int = 47808


@dataclass
class UpdateConfig:
    interval: int | None = None
    mode: str | None = None


@dataclass
class BindingMapping:
    """Value transform between southbound payload and BACnet presentValue."""

    type: str = "real"  # real | boolean | unsigned | enum
    scale: float = 1.0
    offset: float = 0.0
    value_path: str | None = None
    enum_map: dict[str, str] = field(default_factory=dict)


@dataclass
class BindingSpec:
    """Southbound binding for one object (southbound-binding.md §1)."""

    protocol: str  # mqtt | zeromq | wot | grpc
    direction: BindingDirection = BindingDirection.telemetry
    address: str | None = None  # explicit channel/topic; else derived (local_id-first)
    mapping: BindingMapping = field(default_factory=BindingMapping)


@dataclass
class BacnetObjectSpec:
    """A BACnet object as it will appear in simulator.yaml."""

    point_id: str
    object_type: BacnetObjectType
    object_instance: int
    object_name: str
    present_value: float | int | bool | None = None
    units: str | None = None
    min_pres_value: float | None = None
    max_pres_value: float | None = None
    state_text: list[str] = field(default_factory=list)
    active_text: str | None = None
    inactive_text: str | None = None
    scale: float = 1.0
    writable: bool = False
    description: str = ""
    update: UpdateConfig = field(default_factory=UpdateConfig)
    metadata: dict[str, object] = field(default_factory=dict)
    binding: BindingSpec | None = None


@dataclass
class SimulatorConfig:
    bbc: BbcConfig
    network: NetworkConfig
    objects: list[BacnetObjectSpec] = field(default_factory=list)
    mode: RuntimeMode = RuntimeMode.simulator
