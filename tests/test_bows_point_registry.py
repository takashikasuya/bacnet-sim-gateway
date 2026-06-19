"""#73/#74 — PointRegistry: shared point list for ingress and egress resolution."""

from __future__ import annotations

import pytest

from bbc_sim.bows.point_registry import PointRegistry
from bbc_sim.models import BacnetObjectSpec, BacnetObjectType


def _spec(point_id: str, object_type: BacnetObjectType, instance: int) -> BacnetObjectSpec:
    return BacnetObjectSpec(
        point_id=point_id,
        object_type=object_type,
        object_instance=instance,
        object_name=f"{point_id}-name",
    )


@pytest.fixture
def registry() -> PointRegistry:
    return PointRegistry(
        [
            _spec("p-ai-1", BacnetObjectType.analogInput, 1),
            _spec("p-av-7", BacnetObjectType.analogValue, 7),
            _spec("p-bv-3", BacnetObjectType.binaryValue, 3),
            _spec("p-mv-5", BacnetObjectType.multiStateValue, 5),
        ]
    )


def test_resolve_point_id_known(registry: PointRegistry) -> None:
    result = registry.resolve_point_id("p-av-7")
    assert result == (BacnetObjectType.analogValue, 7)


def test_resolve_point_id_unknown_returns_none(registry: PointRegistry) -> None:
    assert registry.resolve_point_id("does-not-exist") is None


def test_resolve_bacnet_known(registry: PointRegistry) -> None:
    result = registry.resolve_bacnet(BacnetObjectType.binaryValue, 3)
    assert result == "p-bv-3"


def test_resolve_bacnet_unknown_returns_none(registry: PointRegistry) -> None:
    assert registry.resolve_bacnet(BacnetObjectType.analogValue, 999) is None


def test_empty_registry_returns_none_for_all(registry: PointRegistry) -> None:
    empty = PointRegistry([])
    assert empty.resolve_point_id("p-av-7") is None
    assert empty.resolve_bacnet(BacnetObjectType.analogValue, 7) is None


def test_from_specs_builds_both_directions() -> None:
    specs = [
        _spec("pt-a", BacnetObjectType.analogInput, 1),
        _spec("pt-b", BacnetObjectType.binaryInput, 2),
    ]
    reg = PointRegistry(specs)
    assert reg.resolve_point_id("pt-a") == (BacnetObjectType.analogInput, 1)
    assert reg.resolve_bacnet(BacnetObjectType.binaryInput, 2) == "pt-b"
