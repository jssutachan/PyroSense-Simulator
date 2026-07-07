"""End-to-end tests of the fleet-sim CLI (no AWS anywhere)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pyrosense_sim.fleet.cli import app
from tests.fleet.site_fixture import write_site

runner = CliRunner()


@pytest.fixture
def site(tmp_path: Path) -> Path:
    return write_site(tmp_path / "sensores.geojson")


@pytest.fixture
def scenario(tmp_path: Path) -> Path:
    path = tmp_path / "scenario.yaml"
    path.write_text("name: cli-test\nduration_hours: 0.25\nseed: 3\n", encoding="utf-8")
    return path


def test_run_to_stdout_emits_valid_ndjson(site: Path, scenario: Path) -> None:
    result = runner.invoke(
        app,
        ["run", "--site", str(site), "--scenario", str(scenario), "--speed", "1000000"],
    )
    assert result.exit_code == 0, result.output
    data_lines = [line for line in result.output.splitlines() if line.startswith("{")]
    assert len(data_lines) == 9  # 3 nodes x 3 samples in 0.25 h
    assert all(json.loads(line)["schema_version"] == "1.0" for line in data_lines)


def test_run_to_file_writes_ndjson(site: Path, scenario: Path, tmp_path: Path) -> None:
    out = tmp_path / "telemetry" / "run.ndjson"
    result = runner.invoke(
        app,
        [
            "run",
            "--site",
            str(site),
            "--scenario",
            str(scenario),
            "--publisher",
            "file",
            "--out",
            str(out),
            "--speed",
            "1000000",
        ],
    )
    assert result.exit_code == 0, result.output
    assert len(out.read_text(encoding="utf-8").splitlines()) == 9


def test_invalid_scenario_key_fails(site: Path, tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("name: x\nvelocidad: 1\n", encoding="utf-8")
    result = runner.invoke(app, ["run", "--site", str(site), "--scenario", str(bad)])
    assert result.exit_code != 0
