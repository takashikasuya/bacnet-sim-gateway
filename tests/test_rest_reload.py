"""EP-007.4 — /pointlist and /pointlist/reload (PR-F-056, ADR-004)."""

from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient

from bbc_sim.rest.api import create_app
from bbc_sim.rest.reload import PointListReloader, _compute_diff
from bbc_sim.rest.status import StatusProvider
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.simulator_runtime.runtime import Runtime
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list
from bbc_sim.yaml_generator.yaml_io import dump_config


@pytest.fixture
def reload_setup(tmp_path, sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="bbc-r", device_id=5001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    source = tmp_path / "sim.yaml"
    dump_config(cfg, source)
    bapp = build_application(cfg, with_network=False)
    runtime = Runtime.__new__(Runtime)
    runtime.config = cfg
    runtime.app = bapp
    runtime.engine = None
    runtime.manager = None
    reloader = PointListReloader(source_path=source, runtime=runtime)
    status = StatusProvider(config=cfg, app=bapp, bound=False, get_manager=lambda: None)
    client = TestClient(create_app(bapp, cfg, status=status, reloader=reloader))
    try:
        yield client, reloader, cfg, source, runtime
    finally:
        bapp.close()


def test_pointlist_info_endpoint(reload_setup):
    client, reloader, cfg, source, _ = reload_setup
    resp = client.get("/pointlist")
    assert resp.status_code == 200
    data = resp.json()
    assert data["object_count"] == len(cfg.objects)
    assert str(source) in (data["source_path"] or "")


def test_pointlist_reload_applied(reload_setup):
    """Reload with unchanged YAML → status=applied."""
    client, _, _, _, _ = reload_setup
    resp = client.post("/pointlist/reload")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "applied"
    assert data["errors"] == []


def test_reload_live_applies_description_and_tags(reload_setup):
    """Non-structural edits (description, tags) are applied to the live object (EP-009.5)."""
    from bbc_sim.bacnet_objects.builder import spec_to_oid
    from bbc_sim.yaml_generator.yaml_io import dump_config, load_config

    _, reloader, cfg, source, runtime = reload_setup
    pid = cfg.objects[0].point_id

    # Edit the on-disk YAML: change description and tags for the first object.
    on_disk = load_config(source)
    on_disk.objects[0].description = "live-updated description"
    on_disk.objects[0].tags = ["updated-tag"]
    dump_config(on_disk, source)

    result = reloader.apply()
    assert result["status"] == "applied"
    assert pid in result["diff"]["modified_live"]

    obj = runtime.app.get_object_id(spec_to_oid(cfg.objects[0]))
    assert str(obj.description) == "live-updated description"
    tag_names = [str(getattr(t, "name", t)) for t in (obj.tags or [])]
    assert "updated-tag" in tag_names


def test_pointlist_reload_no_source(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    bapp = build_application(cfg, with_network=False)
    runtime = Runtime.__new__(Runtime)
    runtime.config = cfg
    runtime.app = bapp
    runtime.engine = None
    runtime.manager = None
    reloader = PointListReloader(source_path=None, runtime=runtime)
    client = TestClient(create_app(bapp, cfg, reloader=reloader))
    try:
        resp = client.post("/pointlist/reload")
        assert resp.status_code == 200
        assert resp.json()["status"] == "no_source"
    finally:
        bapp.close()


def test_reload_validation_failure_leaves_config_unchanged(reload_setup):
    """Corrupt YAML → validation_failed with no config mutation (ADR-004 safety gate)."""
    _, reloader, cfg, source, _ = reload_setup
    original_count = len(cfg.objects)
    source.write_text("bbc:\n  bbc_id: x\n  device_id: 0\n")
    result = reloader.apply()
    assert result["status"] in ("validation_failed", "read_error")
    assert len(cfg.objects) == original_count  # unchanged


def test_compute_diff_added_and_removed(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    new_cfg = copy.deepcopy(cfg)

    # remove first object, keep the rest
    removed_id = cfg.objects[0].point_id
    new_cfg.objects = cfg.objects[1:]

    diff, needs_restart = _compute_diff(cfg, new_cfg)
    assert removed_id in diff.removed
    assert needs_restart is False  # removal alone is live-applicable


def test_compute_diff_structural_change_requires_restart(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    new_cfg = copy.deepcopy(cfg)

    # change object_instance on the first object (structural)
    new_cfg.objects[0].object_instance = 9999

    diff, needs_restart = _compute_diff(cfg, new_cfg)
    assert new_cfg.objects[0].point_id in diff.modified_restart
    assert needs_restart is True


def test_compute_diff_description_change_is_live(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    new_cfg = copy.deepcopy(cfg)
    new_cfg.objects[0].description = "changed description"

    diff, needs_restart = _compute_diff(cfg, new_cfg)
    assert new_cfg.objects[0].point_id in diff.modified_live
    assert needs_restart is False


def test_reload_preserves_bbc_id(reload_setup, tmp_path):
    """bbc_id must not be changed by reload (ADR-003)."""
    _, reloader, cfg, source, _ = reload_setup
    original_bbc_id = cfg.bbc.bbc_id
    result = reloader.apply()
    assert result["status"] in ("applied", "restart_required")
    assert cfg.bbc.bbc_id == original_bbc_id


def test_503_without_reloader(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    bapp = build_application(cfg, with_network=False)
    client = TestClient(create_app(bapp, cfg))
    try:
        assert client.get("/pointlist").status_code == 503
        assert client.post("/pointlist/reload").status_code == 503
    finally:
        bapp.close()
