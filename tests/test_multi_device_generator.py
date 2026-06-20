"""multi-device generator (ADR-011 multi-device mode) tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bbc_sim.cli import app
from bbc_sim.models import BacnetObjectType
from bbc_sim.yaml_generator.pointlist import read_point_list

runner = CliRunner()


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

def _make_multi_device_csv(tmp_path: Path) -> Path:
    """CSV with 4 points across 2 BACnet devices (DEV-A and DEV-B).

    Both devices use instance_no_bacnet 1 and 2 for analogInput — this would
    trigger collision warnings in aggregated mode.
    """
    header = (
        "gateway_id,device_id,device_name,device_type,site,building,floor,"
        "installation_area,target_area,panel,point_type,point_specification,point_id,"
        "point_name,writable,interval,unit,max_pres_value,min_pres_value,labels,scale,"
        "tags,supplier,owner,description,local_id,device_id_bacnet,instance_no_bacnet,"
        "object_type_bacnet"
    )
    rows = [
        "GW1,D1,d,AHU,s,b,1F,a,a,,Temperature,Measurement,DEV-A-AI-1,Temp A1,false,60,℃,50,-10,,1.0,,,,,L1,DEV-A,1,Analog-Input",
        "GW1,D1,d,AHU,s,b,1F,a,a,,Temperature,Measurement,DEV-A-AI-2,Temp A2,false,60,℃,50,-10,,1.0,,,,,L2,DEV-A,2,Analog-Input",
        # DEV-B reuses instance 1 and 2 — collision in aggregated, fine in multi-device
        "GW1,D1,d,AHU,s,b,1F,a,a,,Temperature,Measurement,DEV-B-AI-1,Temp B1,false,60,℃,50,-10,,1.0,,,,,L3,DEV-B,1,Analog-Input",
        "GW1,D1,d,AHU,s,b,1F,a,a,,Temperature,Measurement,DEV-B-AI-2,Temp B2,false,60,℃,50,-10,,1.0,,,,,L4,DEV-B,2,Analog-Input",
    ]
    path = tmp_path / "multi_device.csv"
    path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Cycle 1: grouping by device_id_bacnet
# ---------------------------------------------------------------------------

def test_multi_device_config_has_one_entry_per_bacnet_device(tmp_path):
    from bbc_sim.yaml_generator.generator import generate_multi_device_config

    points = read_point_list(_make_multi_device_csv(tmp_path))
    config, warnings = generate_multi_device_config(
        points, base_bbc_id="bbc-local-001", base_device_id=1001
    )
    assert len(config.devices) == 2


# ---------------------------------------------------------------------------
# Cycle 2: no collision warnings for same instance_no across devices
# ---------------------------------------------------------------------------

def test_multi_device_produces_no_instance_collision_warnings(tmp_path):
    from bbc_sim.yaml_generator.generator import generate_multi_device_config

    points = read_point_list(_make_multi_device_csv(tmp_path))
    _, warnings = generate_multi_device_config(
        points, base_bbc_id="bbc-local-001", base_device_id=1001
    )
    collision_warnings = [w for w in warnings if "already in use" in w]
    assert collision_warnings == []


# ---------------------------------------------------------------------------
# Cycle 3: instance_no_bacnet respected within each device
# ---------------------------------------------------------------------------

def test_multi_device_respects_instance_no_bacnet_per_device(tmp_path):
    from bbc_sim.yaml_generator.generator import generate_multi_device_config

    points = read_point_list(_make_multi_device_csv(tmp_path))
    config, _ = generate_multi_device_config(
        points, base_bbc_id="bbc-local-001", base_device_id=1001
    )
    # Both DEV-A and DEV-B should have analogInput:1 and analogInput:2
    for dev_cfg in config.devices:
        ai_instances = sorted(
            o.object_instance
            for o in dev_cfg.objects
            if o.object_type == BacnetObjectType.analogInput
        )
        assert ai_instances == [1, 2]


# ---------------------------------------------------------------------------
# Cycle 4: device IDs assigned sequentially from base
# ---------------------------------------------------------------------------

def test_multi_device_assigns_device_ids_from_base(tmp_path):
    from bbc_sim.yaml_generator.generator import generate_multi_device_config

    points = read_point_list(_make_multi_device_csv(tmp_path))
    config, _ = generate_multi_device_config(
        points, base_bbc_id="bbc-local-001", base_device_id=2000
    )
    device_ids = [dev.bbc.device_id for dev in config.devices]
    assert device_ids == [2000, 2001]


# ---------------------------------------------------------------------------
# Cycle 5: YAML dump / load roundtrip
# ---------------------------------------------------------------------------

def test_multi_device_yaml_roundtrip(tmp_path):
    from bbc_sim.yaml_generator.generator import generate_multi_device_config
    from bbc_sim.yaml_generator.yaml_io import dump_multi_device_config, load_multi_device_config

    points = read_point_list(_make_multi_device_csv(tmp_path))
    config, _ = generate_multi_device_config(
        points, base_bbc_id="bbc-local-001", base_device_id=1001
    )
    out = tmp_path / "multi.yaml"
    dump_multi_device_config(config, out)

    loaded = load_multi_device_config(out)
    assert len(loaded.devices) == 2
    total_objects = sum(len(d.objects) for d in loaded.devices)
    assert total_objects == 4


# ---------------------------------------------------------------------------
# Cycle 6: validate_multi_device_config
# ---------------------------------------------------------------------------

def test_validate_multi_device_config_allows_cross_device_instance_reuse(tmp_path):
    from bbc_sim.yaml_generator.generator import generate_multi_device_config
    from bbc_sim.yaml_generator.yaml_io import validate_multi_device_config

    points = read_point_list(_make_multi_device_csv(tmp_path))
    config, _ = generate_multi_device_config(
        points, base_bbc_id="bbc-local-001", base_device_id=1001
    )
    errors = validate_multi_device_config(config)
    assert errors == []


def test_validate_multi_device_config_rejects_intra_device_instance_duplicate(tmp_path):
    from bbc_sim.models import BacnetObjectSpec, BbcConfig, MultiDeviceConfig, NetworkConfig, SimulatorConfig
    from bbc_sim.yaml_generator.yaml_io import validate_multi_device_config

    def _ai(point_id, instance):
        return BacnetObjectSpec(
            point_id=point_id,
            object_type=BacnetObjectType.analogInput,
            object_instance=instance,
            object_name=point_id,
        )

    dev = SimulatorConfig(
        bbc=BbcConfig(bbc_id="bbc-0", device_id=1001),
        network=NetworkConfig(),
        objects=[_ai("PT1", 1), _ai("PT2", 1)],  # duplicate instance within same device
    )
    config = MultiDeviceConfig(devices=[dev])
    errors = validate_multi_device_config(config)
    assert any("duplicate" in e for e in errors)


# ---------------------------------------------------------------------------
# Cycle 7: CLI --device-mapping multi-device
# ---------------------------------------------------------------------------

def test_cli_multi_device_mapping_produces_multi_device_yaml(tmp_path):
    from bbc_sim.yaml_generator.yaml_io import load_multi_device_config

    csv = _make_multi_device_csv(tmp_path)
    out = tmp_path / "multi.yaml"
    result = runner.invoke(
        app,
        [
            "generate-yaml",
            "-i", str(csv),
            "-o", str(out),
            "--device-mapping", "multi-device",
            "--bbc-id", "bbc-local-001",
            "--bacnet-device-id", "1001",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    loaded = load_multi_device_config(out)
    assert len(loaded.devices) == 2


def test_cli_multi_device_mapping_no_collision_warnings(tmp_path):
    csv = _make_multi_device_csv(tmp_path)
    out = tmp_path / "multi.yaml"
    result = runner.invoke(
        app,
        [
            "generate-yaml",
            "-i", str(csv),
            "-o", str(out),
            "--device-mapping", "multi-device",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "already in use" not in result.output


def test_cli_default_device_mapping_is_aggregated(tmp_path):
    """--device-mapping omitted → existing aggregated behaviour unchanged."""
    csv = _make_multi_device_csv(tmp_path)
    out = tmp_path / "sim.yaml"
    from bbc_sim.yaml_generator.yaml_io import load_config
    result = runner.invoke(
        app, ["generate-yaml", "-i", str(csv), "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    cfg = load_config(out)
    assert len(cfg.objects) == 4  # still one flat device


# ---------------------------------------------------------------------------
# Bug fixes
# ---------------------------------------------------------------------------

def test_load_multi_device_config_tolerates_null_devices(tmp_path):
    """devices: null in YAML must not raise TypeError."""
    import yaml
    from bbc_sim.yaml_generator.yaml_io import load_multi_device_config

    bad = tmp_path / "null_devices.yaml"
    bad.write_text(yaml.safe_dump({"device_mapping": "multi-device", "devices": None}), encoding="utf-8")
    config = load_multi_device_config(bad)
    assert config.devices == []


def test_validate_yaml_auto_detects_multi_device_format(tmp_path):
    """bbc-sim validate must not report 'invalid simulator.yaml: bbc' for multi-device YAML."""
    from bbc_sim.yaml_generator.yaml_io import validate_yaml
    from bbc_sim.yaml_generator.generator import generate_multi_device_config
    from bbc_sim.yaml_generator.yaml_io import dump_multi_device_config

    points = read_point_list(_make_multi_device_csv(tmp_path))
    config, _ = generate_multi_device_config(points, base_bbc_id="bbc-x", base_device_id=1001)
    out = tmp_path / "multi.yaml"
    dump_multi_device_config(config, out)

    errors = validate_yaml(out)
    assert errors == []


def test_multi_device_object_names_are_unique_per_device(tmp_path):
    """Each device must get a distinct object_name (BACnet uniqueness requirement)."""
    from bbc_sim.yaml_generator.generator import generate_multi_device_config

    points = read_point_list(_make_multi_device_csv(tmp_path))
    config, _ = generate_multi_device_config(points, base_bbc_id="bbc-x", base_device_id=1001)
    names = [d.bbc.object_name for d in config.devices]
    assert len(names) == len(set(names)), f"duplicate object_names: {names}"


def test_validate_multi_device_config_rejects_duplicate_device_ids(tmp_path):
    """Cross-device duplicate device_id must be flagged."""
    from bbc_sim.models import BbcConfig, MultiDeviceConfig, NetworkConfig, SimulatorConfig
    from bbc_sim.yaml_generator.yaml_io import validate_multi_device_config

    def _dev(device_id):
        return SimulatorConfig(
            bbc=BbcConfig(bbc_id=f"bbc-{device_id}", device_id=device_id),
            network=NetworkConfig(),
        )

    config = MultiDeviceConfig(devices=[_dev(1001), _dev(1001)])  # duplicate
    errors = validate_multi_device_config(config)
    assert any("device_id" in e for e in errors)
