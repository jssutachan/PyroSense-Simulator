"""Tests for planner configuration loading (boundary validation)."""

from pathlib import Path

import pytest

from pyrosense_sim.planner.params import PlannerParams, load_params


def write_yaml(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "params.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_none_path_gives_pure_defaults() -> None:
    params = load_params(None)
    assert params == PlannerParams()
    assert params.densities_ha == {1: 4.0, 2: 10.0, 3: 25.0}


def test_partial_yaml_keeps_defaults_for_absent_keys(tmp_path: Path) -> None:
    params = load_params(write_yaml(tmp_path, "seed: 99\njitter_m: 10.0\n"))
    assert params.seed == 99
    assert params.jitter_m == 10.0
    assert params.max_slope_deg == 45.0  # default preserved


def test_densities_block_maps_tier_keys(tmp_path: Path) -> None:
    params = load_params(write_yaml(tmp_path, "densities_ha:\n  t1: 2.0\n  t2: 8.0\n  t3: 30.0\n"))
    assert params.densities_ha == {1: 2.0, 2: 8.0, 3: 30.0}


def test_zones_geojson_becomes_a_path(tmp_path: Path) -> None:
    params = load_params(write_yaml(tmp_path, "zones_geojson: config/zonas.geojson\n"))
    assert params.zones_geojson == Path("config/zonas.geojson")


def test_empty_file_gives_defaults(tmp_path: Path) -> None:
    assert load_params(write_yaml(tmp_path, "")) == PlannerParams()


def test_unknown_keys_fail_early_with_valid_key_list(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"unknown config keys.*jitter_metros.*valid keys"):
        load_params(write_yaml(tmp_path, "jitter_metros: 10\n"))


def test_non_mapping_yaml_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be a YAML mapping"):
        load_params(write_yaml(tmp_path, "- just\n- a\n- list\n"))


def test_incomplete_densities_block_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="t1/t2/t3"):
        load_params(write_yaml(tmp_path, "densities_ha:\n  t1: 4.0\n"))
