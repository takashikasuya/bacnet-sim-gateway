"""EP-005 — semantic tags (ADR-006/012, AC-14, PR-F-016/017/018)."""

from __future__ import annotations

import asyncio

from bbc_sim.semantic.brick import derive_tags, has_mapping
from bbc_sim.services.client import build_client, read_property
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list

# ---- Brick-derived tag generation (deterministic) ----


def test_derive_tags_is_deterministic_and_sorted():
    a = derive_tags("AirHandlingUnit", "Temperature")
    b = derive_tags("AirHandlingUnit", "Temperature")
    assert a == b == sorted(a)
    assert "point" in a and "sensor" in a and "temp" in a and "ahu" in a


def test_derive_tags_unknown_types_base_only():
    tags = derive_tags("Spaceship", "Warp Core")
    assert tags == ["point"]
    assert has_mapping("Spaceship", "Warp Core") is False


def test_generator_assigns_tags_and_search_tags(sample_pointlist):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1)
    pt001 = next(o for o in cfg.objects if o.point_id == "PT001")  # Temperature on AHU
    assert "temp" in pt001.tags and "sensor" in pt001.tags
    # SBCO `tags` column kept verbatim as search_tags (different concept)
    assert pt001.metadata["search_tags"] == ["temperature", "room101"]


def test_tags_survive_yaml_roundtrip(sample_pointlist, tmp_path):
    from bbc_sim.yaml_generator.yaml_io import dump_config, load_config

    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1)
    path = tmp_path / "sim.yaml"
    dump_config(cfg, path)
    loaded = load_config(path)
    pt001 = next(o for o in loaded.objects if o.point_id == "PT001")
    assert "temp" in pt001.tags
    assert pt001.metadata["search_tags"] == ["temperature", "room101"]


# ---- tags readable over BACnet RP (AC-14, PR-F-016) ----


async def test_tags_readable_via_read_property(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    server = build_application(cfg)
    client = build_client(f"127.0.0.1:{free_port()}")
    target = f"127.0.0.1:{cfg.network.port}"
    await asyncio.sleep(0.3)
    try:
        tags = await read_property(client, target, "analog-input,1001", "tags")
        names = [str(nv.name) for nv in tags]
        assert "temp" in names and "sensor" in names
    finally:
        client.close()
        server.close()


def test_tags_set_on_built_object(sample_pointlist):
    from bbc_sim.bacnet_objects.builder import build_object

    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1)
    pt001 = next(o for o in cfg.objects if o.point_id == "PT001")
    obj = build_object(pt001)
    names = [str(nv.name) for nv in obj.tags]
    assert set(names) == set(pt001.tags)


def test_search_tags_are_deduplicated(tmp_path):
    # SBCO tags column kept verbatim except duplicate removal (Issue #26 / review #36).
    from bbc_sim.models import SbcoPoint

    p = SbcoPoint(
        gateway_id="GW",
        device_id="D",
        device_name="d",
        device_type="Sensor",
        site="",
        building="b",
        floor="1F",
        installation_area="a",
        target_area="",
        panel="",
        point_type="Temperature",
        point_specification="Measurement",
        point_id="P1",
        point_name="n",
        writable=False,
        interval=None,
        unit="degC",
        max_pres_value=None,
        min_pres_value=None,
        labels=[],
        scale=1.0,
        tags=["room", "temp", "room"],
        supplier="",
        owner="",
        description="",
        local_id="L1",
        device_id_bacnet="",
        instance_no_bacnet=None,
        object_type_bacnet="Analog-Input",
    )
    cfg, _ = generate_config([p], bbc_id="b", device_id=1001)
    assert cfg.objects[0].metadata["search_tags"] == ["room", "temp"]
