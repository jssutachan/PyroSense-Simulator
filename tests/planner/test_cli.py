"""End-to-end tests of the site-planner CLI (typer runner, synthetic inputs)."""

import json
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import box, mapping
from typer.testing import CliRunner

from pyrosense_sim.planner.cli import app
from tests.planner.synthetic_dem import write_dem

runner = CliRunner()


@pytest.fixture
def inputs(tmp_path: Path) -> dict[str, Path]:
    data = np.tile(0.1 * np.arange(100), (50, 1)).astype(np.float64)
    dem = write_dem(tmp_path / "dem.tif", data)
    aoi = tmp_path / "aoi.geojson"
    aoi.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": mapping(box(-74.09, 4.51, -74.03, 4.56)),
                        "properties": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    config = tmp_path / "params.yaml"
    config.write_text("seed: 7\ngateway_capacity: 40\n", encoding="utf-8")
    return {"dem": dem, "aoi": aoi, "config": config, "out": tmp_path / "out"}


def test_generate_writes_the_three_artifacts(inputs: dict[str, Path]) -> None:
    result = runner.invoke(
        app,
        [
            "generate",
            "--dem",
            str(inputs["dem"]),
            "--aoi",
            str(inputs["aoi"]),
            "--config",
            str(inputs["config"]),
            "--out",
            str(inputs["out"]),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Plan generated" in result.output
    for name in ("sensors.geojson", "gateways.geojson", "site-report.md"):
        assert (inputs["out"] / name).exists()


def test_generate_with_preview_writes_png(inputs: dict[str, Path]) -> None:
    result = runner.invoke(
        app,
        [
            "generate",
            "--dem",
            str(inputs["dem"]),
            "--aoi",
            str(inputs["aoi"]),
            "--out",
            str(inputs["out"]),
            "--preview",
        ],
    )
    assert result.exit_code == 0, result.output
    preview = inputs["out"] / "preview.png"
    assert preview.exists()
    assert preview.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_defaults_apply_without_config(inputs: dict[str, Path]) -> None:
    result = runner.invoke(
        app,
        [
            "generate",
            "--dem",
            str(inputs["dem"]),
            "--aoi",
            str(inputs["aoi"]),
            "--out",
            str(inputs["out"]),
        ],
    )
    assert result.exit_code == 0, result.output


def test_aoi_must_be_a_polygon(inputs: dict[str, Path], tmp_path: Path) -> None:
    bad_aoi = tmp_path / "bad.geojson"
    bad_aoi.write_text(
        json.dumps({"type": "LineString", "coordinates": [[0, 0], [1, 1]]}), encoding="utf-8"
    )
    result = runner.invoke(
        app,
        [
            "generate",
            "--dem",
            str(inputs["dem"]),
            "--aoi",
            str(bad_aoi),
            "--out",
            str(inputs["out"]),
        ],
    )
    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
