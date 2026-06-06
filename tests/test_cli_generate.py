"""EP-001.3/.4 — generate-yaml / validate / validate-point-list CLI (PR-F-060..062)."""

from __future__ import annotations

from typer.testing import CliRunner

from bbc_sim.cli import app
from bbc_sim.yaml_generator.yaml_io import load_config

runner = CliRunner()


def test_generate_yaml_produces_valid_config(sample_pointlist, tmp_path):
    out = tmp_path / "simulator.yaml"
    result = runner.invoke(
        app,
        ["generate-yaml", "-i", str(sample_pointlist), "-o", str(out),
         "--bbc-id", "bbc-local-001", "--bacnet-device-id", "1001"],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    cfg = load_config(out)
    assert cfg.bbc.bbc_id == "bbc-local-001"
    assert len(cfg.objects) == 8


def test_generate_then_validate(sample_pointlist, tmp_path):
    out = tmp_path / "simulator.yaml"
    runner.invoke(app, ["generate-yaml", "-i", str(sample_pointlist), "-o", str(out)])
    result = runner.invoke(app, ["validate", "-c", str(out)])
    assert result.exit_code == 0, result.output
    assert "valid" in result.output


def test_validate_point_list_ok(sample_pointlist):
    result = runner.invoke(app, ["validate-point-list", "-i", str(sample_pointlist)])
    assert result.exit_code == 0, result.output


def test_validate_point_list_missing_column(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("point_id,point_name\nP1,foo\n", encoding="utf-8")
    result = runner.invoke(app, ["validate-point-list", "-i", str(bad)])
    assert result.exit_code == 1
    assert "gateway_id" in result.output


def test_generate_yaml_output_is_self_validated(sample_pointlist, tmp_path):
    # generate-yaml validates its own output; a clean list yields a valid file.
    out = tmp_path / "simulator.yaml"
    result = runner.invoke(app, ["generate-yaml", "-i", str(sample_pointlist), "-o", str(out)])
    assert result.exit_code == 0
    # the generated file passes `validate`
    assert runner.invoke(app, ["validate", "-c", str(out)]).exit_code == 0


def test_inference_emits_warning(sample_pointlist, tmp_path):
    # PT002/PT003/PT005 lack object_type_bacnet -> inference warnings on stderr.
    out = tmp_path / "simulator.yaml"
    result = runner.invoke(
        app, ["generate-yaml", "-i", str(sample_pointlist), "-o", str(out)]
    )
    assert result.exit_code == 0
    assert "warning" in result.output.lower()
