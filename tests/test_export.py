"""EP-006 — standards artifacts & semantic export (PR-F-072/073, §19)."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from bbc_sim.cli import app
from bbc_sim.export.artifacts import export, to_ede, to_jsonld, to_pics, to_wot_td
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list

runner = CliRunner()


@pytest.fixture
def config(sample_pointlist):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="bbc-1", device_id=1001)
    return cfg


def test_ede_lists_all_objects(config):
    csv_text = to_ede(config)
    lines = [ln for ln in csv_text.splitlines() if ln and not ln.startswith("# ")]
    # header + 8 objects
    assert len(lines) == 1 + 8
    assert "analogInput" in csv_text
    assert "PT001" in csv_text


def test_pics_lists_object_types_and_bibbs(config):
    pics = to_pics(config)
    assert "DS-RP-B" in pics
    assert "analogInput" in pics
    assert "BACnet/IP" in pics


def test_jsonld_is_brick_graph(config):
    doc = to_jsonld(config)
    assert "@context" in doc and "brick" in doc["@context"]
    nodes = doc["@graph"]
    controller = next(n for n in nodes if n["@type"] == "brick:Building_Controller")
    assert len(controller["brick:hasPoint"]) == 8
    temp = next(n for n in nodes if n["@id"].endswith("/PT001"))
    assert temp["@type"] == "brick:Air_Temperature_Sensor"
    assert "temp" in temp["haystack:tags"]


def test_wot_td_has_properties(config):
    td = to_wot_td(config)
    assert td["@type"] == "Thing"
    assert len(td["properties"]) == 8
    assert td["properties"]["PT001"]["readOnly"] is True   # analog-input
    assert td["properties"]["PT006"]["readOnly"] is False  # analog-value (writable)


def test_export_unknown_format_raises(config):
    with pytest.raises(ValueError):
        export(config, "hologram")


def test_export_cli_writes_file(sample_pointlist, tmp_path):
    sim = tmp_path / "sim.yaml"
    runner.invoke(app, ["generate-yaml", "-i", str(sample_pointlist), "-o", str(sim)])
    out = tmp_path / "out.jsonld"
    result = runner.invoke(app, ["export", "-f", "jsonld", "-c", str(sim), "-o", str(out)])
    assert result.exit_code == 0, result.output
    doc = json.loads(out.read_text())
    assert doc["@graph"]


def test_export_cli_rejects_bad_format(sample_pointlist, tmp_path):
    sim = tmp_path / "sim.yaml"
    runner.invoke(app, ["generate-yaml", "-i", str(sample_pointlist), "-o", str(sim)])
    result = runner.invoke(app, ["export", "-f", "nope", "-c", str(sim)])
    assert result.exit_code == 1
