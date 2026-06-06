"""EP-001.1 — SBCO CSV reader + validation + gateway_id != bbc_id (TS-01, PR-F-002/003)."""

from __future__ import annotations

import pytest

from bbc_sim.models import PointListError
from bbc_sim.yaml_generator.pointlist import read_point_list, validate_point_list


def test_reads_all_rows(sample_pointlist):
    points = read_point_list(sample_pointlist)
    assert len(points) == 8
    assert points[0].point_id == "PT001"
    assert points[0].point_name == "Supply Air Temperature"


def test_writable_normalized_to_bool(sample_pointlist):
    points = read_point_list(sample_pointlist)
    by_id = {p.point_id: p for p in points}
    assert by_id["PT001"].writable is False
    assert by_id["PT004"].writable is True


def test_labels_split_on_double_ampersand(sample_pointlist):
    points = read_point_list(sample_pointlist)
    by_id = {p.point_id: p for p in points}
    assert by_id["PT005"].labels == ["Low", "Medium", "High"]
    assert by_id["PT001"].labels == []


def test_tags_split_on_double_ampersand(sample_pointlist):
    points = read_point_list(sample_pointlist)
    assert points[0].tags == ["temperature", "room101"]


def test_scale_and_numeric_fields(sample_pointlist):
    points = read_point_list(sample_pointlist)
    by_id = {p.point_id: p for p in points}
    assert by_id["PT001"].scale == 1.0
    assert by_id["PT001"].max_pres_value == 50.0
    assert by_id["PT001"].min_pres_value == -10.0
    assert by_id["PT003"].max_pres_value is None


def test_missing_required_column_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("point_id,point_name\nPT001,Foo\n", encoding="utf-8")
    with pytest.raises(PointListError) as exc:
        read_point_list(bad)
    assert "gateway_id" in str(exc.value)


def test_duplicate_point_id_is_error(tmp_path, sample_pointlist):
    text = sample_pointlist.read_text(encoding="utf-8").splitlines()
    dup = tmp_path / "dup.csv"
    dup.write_text("\n".join([text[0], text[1], text[1]]) + "\n", encoding="utf-8")
    errors = validate_point_list(dup)
    assert any("PT001" in e and "duplicate" in e.lower() for e in errors)


def test_writable_normalizes_yes_no(tmp_path, sample_pointlist):
    lines = sample_pointlist.read_text(encoding="utf-8").splitlines()
    row = lines[1].split(",")
    row[14] = "yes"  # writable column
    out = tmp_path / "yn.csv"
    out.write_text(lines[0] + "\n" + ",".join(row) + "\n", encoding="utf-8")
    points = read_point_list(out)
    assert points[0].writable is True


def test_clean_list_validates_without_errors(sample_pointlist):
    assert validate_point_list(sample_pointlist) == []
