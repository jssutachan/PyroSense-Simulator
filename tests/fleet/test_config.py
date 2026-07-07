"""Tests for scenario configuration loading and strict validation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from pyrosense_sim.fleet.config import ScenarioConfig, load_scenario

REPO_ROOT = Path(__file__).parents[2]


def write_scenario(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "scenario.yaml"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.parametrize("name", ["baseline.yaml", "temporada_seca.yaml"])
def test_shipped_scenarios_are_valid(name: str) -> None:
    config = load_scenario(REPO_ROOT / "scenarios" / name)
    assert config.duration_hours == 24.0
    assert config.start_time.tzinfo is not None


def test_unknown_key_is_rejected(tmp_path: Path) -> None:
    path = write_scenario(tmp_path, "name: x\nduracion_horas: 24\n")
    with pytest.raises(ValidationError, match="duracion_horas"):
        load_scenario(path)


def test_unknown_nested_key_is_rejected(tmp_path: Path) -> None:
    path = write_scenario(tmp_path, "name: x\nenvironment:\n  temperatura: 20\n")
    with pytest.raises(ValidationError, match="temperatura"):
        load_scenario(path)


def test_naive_start_time_is_rejected(tmp_path: Path) -> None:
    path = write_scenario(tmp_path, "name: x\nstart_time: 2026-01-15 00:00:00\n")
    with pytest.raises(ValidationError, match="timezone-aware"):
        load_scenario(path)


def test_non_mapping_yaml_is_rejected(tmp_path: Path) -> None:
    path = write_scenario(tmp_path, "- a\n- b\n")
    with pytest.raises(ValueError, match="YAML mapping"):
        load_scenario(path)


def test_defaults_are_reasonable() -> None:
    config = ScenarioConfig(name="defaults")
    assert config.node.t_normal_s == 300.0
    assert config.node.t_alert_s == 30.0
    assert config.duration_s == 24 * 3600
