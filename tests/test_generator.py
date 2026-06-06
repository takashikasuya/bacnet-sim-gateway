"""EP-001.3 / EP-001.4 — YAML generator (aggregated) + schema I/O + validate.

(PR-F-091/092, ADR-011, ADR-004; requirements §6/§14)
"""

from __future__ import annotations

import pytest

from bbc_sim.models import BacnetObjectType, SimulatorConfig
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list
from bbc_sim.yaml_generator.yaml_io import (
    config_to_dict,
    dump_config,
    load_config,
    validate_config,
)


@pytest.fixture
def config(sample_pointlist) -> SimulatorConfig:
    points = read_point_list(sample_pointlist)
    cfg, _warnings = generate_config(points, bbc_id="bbc-local-001", device_id=1001)
    return cfg


def test_aggregated_single_device(config):
    # device-mapping = aggregated: the whole list becomes one Virtual B-BC.
    assert config.bbc.bbc_id == "bbc-local-001"
    assert config.bbc.device_id == 1001
    assert len(config.objects) == 8


def test_bbc_id_is_not_gateway_id(sample_pointlist):
    # gateway_id (GW001) must never be reused as bbc_id (ADR-003).
    points = read_point_list(sample_pointlist)
    cfg, _ = generate_config(points, bbc_id="bbc-local-001", device_id=1001)
    assert cfg.bbc.bbc_id != points[0].gateway_id
    assert all(o.metadata.get("gateway_id") == "GW001" for o in cfg.objects)


def test_explicit_instance_honored(config):
    by_id = {o.point_id: o for o in config.objects}
    assert by_id["PT001"].object_instance == 1001
    assert by_id["PT004"].object_instance == 2001


def test_instances_unique_within_type(config):
    seen: dict[BacnetObjectType, set[int]] = {}
    for o in config.objects:
        s = seen.setdefault(o.object_type, set())
        assert o.object_instance not in s, f"collision {o.object_type}:{o.object_instance}"
        s.add(o.object_instance)


def test_auto_assigned_instances_avoid_explicit(config):
    # PT002 is analogInput with no explicit instance; must not collide with PT001/PT008.
    by_id = {o.point_id: o for o in config.objects}
    ai_instances = {o.object_instance for o in config.objects
                    if o.object_type is BacnetObjectType.analogInput}
    assert by_id["PT002"].object_instance in ai_instances
    assert by_id["PT002"].object_instance not in (1001, 1003)


def test_binary_text_from_labels(config):
    by_id = {o.point_id: o for o in config.objects}
    pt004 = by_id["PT004"]  # labels Closed&&Open
    assert pt004.inactive_text == "Closed"
    assert pt004.active_text == "Open"


def test_multistate_state_text_from_labels(config):
    by_id = {o.point_id: o for o in config.objects}
    pt005 = by_id["PT005"]  # Low&&Medium&&High
    assert pt005.state_text == ["Low", "Medium", "High"]


def test_yaml_roundtrip(config, tmp_path):
    path = tmp_path / "simulator.yaml"
    dump_config(config, path)
    loaded = load_config(path)
    assert loaded.bbc.bbc_id == config.bbc.bbc_id
    assert len(loaded.objects) == len(config.objects)
    assert loaded.objects[0].object_type is config.objects[0].object_type


def test_config_dict_matches_spec_schema(config):
    d = config_to_dict(config)
    assert set(d.keys()) == {"bbc", "network", "objects"}
    assert d["bbc"]["device_id"] == 1001
    assert d["network"]["port"] == 47808
    assert d["objects"][0]["object_type"] in {t.value for t in BacnetObjectType}


def test_validate_detects_duplicate_instance(config):
    config.objects[1].object_type = config.objects[0].object_type
    config.objects[1].object_instance = config.objects[0].object_instance
    errors = validate_config(config)
    assert any("instance" in e.lower() for e in errors)


def test_validate_clean_config(config):
    assert validate_config(config) == []
