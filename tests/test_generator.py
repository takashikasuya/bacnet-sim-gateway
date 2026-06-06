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


def test_update_params_survive_yaml_roundtrip(config, tmp_path):
    from bbc_sim.models import UpdateConfig
    from bbc_sim.yaml_generator.yaml_io import dump_config, load_config

    config.objects[0].update = UpdateConfig(
        interval=5, mode="scenario", params={"setpoints": [[0, 10.0], [3, 25.0]]}
    )
    path = tmp_path / "sim.yaml"
    dump_config(config, path)
    loaded = load_config(path)
    o = loaded.objects[0]
    assert o.update.mode == "scenario"
    assert o.update.params["setpoints"] == [[0, 10.0], [3, 25.0]]


def test_yaml_roundtrip(config, tmp_path):
    path = tmp_path / "simulator.yaml"
    dump_config(config, path)
    loaded = load_config(path)
    assert loaded.bbc.bbc_id == config.bbc.bbc_id
    assert len(loaded.objects) == len(config.objects)
    assert loaded.objects[0].object_type is config.objects[0].object_type


def test_config_dict_matches_spec_schema(config):
    d = config_to_dict(config)
    assert set(d.keys()) == {"bbc", "network", "objects", "mode"}
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


# ---- edge cases (from review of EP-001) ----


def test_empty_point_list_produces_empty_valid_config():
    cfg, warnings = generate_config([], bbc_id="bbc-local-001", device_id=1001)
    assert cfg.objects == []
    assert validate_config(cfg) == []


def test_duplicate_explicit_instance_is_resolved_and_warned(tmp_path, sample_pointlist):
    # Two analog-input rows both claiming instance 1001 -> conflict; generator must
    # keep the YAML valid (unique instances) and warn.
    lines = sample_pointlist.read_text(encoding="utf-8").splitlines()
    header, pt001 = lines[0], lines[1].split(",")
    clash = pt001.copy()
    clash[12] = "PT099"  # point_id
    clash[27] = "1001"   # instance_no_bacnet collides with PT001
    out = tmp_path / "clash.csv"
    out.write_text("\n".join([header, lines[1], ",".join(clash)]) + "\n", encoding="utf-8")

    points = read_point_list(out)
    cfg, warnings = generate_config(points, bbc_id="bbc-local-001", device_id=1001)
    assert validate_config(cfg) == []  # no duplicate instances in the result
    assert any("1001" in w and "instance" in w.lower() for w in warnings)


def test_multistate_without_labels_is_flagged():
    from bbc_sim.models import SbcoPoint

    p = SbcoPoint(
        gateway_id="GW", device_id="D", device_name="d", device_type="t", site="",
        building="", floor="", installation_area="", target_area="", panel="",
        point_type="", point_specification="", point_id="P1", point_name="n",
        writable=True, interval=None, unit="", max_pres_value=None, min_pres_value=None,
        labels=[], scale=1.0, tags=[], supplier="", owner="", description="",
        local_id="", device_id_bacnet="", instance_no_bacnet=None,
        object_type_bacnet="Multi-state-Value",
    )
    cfg, _ = generate_config([p], bbc_id="bbc-local-001", device_id=1001)
    errors = validate_config(cfg)
    assert any("state_text" in e for e in errors)
