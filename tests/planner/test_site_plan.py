"""Tests for SitePlan: assembly, serialization schema, determinism, report."""

import json
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import box

from pyrosense_sim.planner.params import PlannerParams
from pyrosense_sim.planner.site_plan import SitePlan
from pyrosense_sim.planner.terrain import TerrainModel
from pyrosense_sim.planner.zones import ZoneSet
from tests.planner.synthetic_dem import write_dem

WIDTH, HEIGHT = 100, 50

# The synthetic stand-in for the Cerros Orientales reference AOI:
# ~10 km x 5.5 km (~5,500 ha) inside the DEM, zones derived by default.
REFERENCE_AOI = box(-74.10, 4.50, -74.01, 4.55)

REQUIRED_SENSOR_PROPERTIES = {
    "device_id",
    "tier",
    "zone_name",
    "elevation_m",
    "slope_deg",
    "gateway_id",
    "has_wind_sensor",
}


def make_terrain(tmp_path: Path) -> TerrainModel:
    data = np.tile(0.1 * np.arange(WIDTH), (HEIGHT, 1)).astype(np.float64)
    return TerrainModel(write_dem(tmp_path / "dem.tif", data))


def reference_plan(tmp_path: Path, seed: int = 0) -> SitePlan:
    terrain = make_terrain(tmp_path)
    zones = ZoneSet.derive_default(REFERENCE_AOI)
    return SitePlan.generate(terrain, zones, PlannerParams(seed=seed))


class TestReferenceAoi:
    def test_total_nodes_in_target_range(self, tmp_path: Path) -> None:
        plan = reference_plan(tmp_path)
        assert 200 <= len(plan.nodes) <= 500

    def test_every_feature_has_all_specified_properties(self, tmp_path: Path) -> None:
        plan = reference_plan(tmp_path)
        collection = plan.sensors_geojson()
        features = collection["features"]
        assert isinstance(features, list)
        assert features
        for feature in features:
            assert set(feature["properties"].keys()) == REQUIRED_SENSOR_PROPERTIES
            assert feature["properties"]["gateway_id"] is not None

    def test_gateways_geojson_lists_every_gateway(self, tmp_path: Path) -> None:
        plan = reference_plan(tmp_path)
        collection = plan.gateways_geojson()
        features = collection["features"]
        assert isinstance(features, list)
        assert len(features) == len(plan.gateways)
        assigned = sum(feature["properties"]["assigned_nodes"] for feature in features)
        assert assigned == len(plan.nodes)


class TestDeterminism:
    def test_same_seed_produces_byte_identical_output(self, tmp_path: Path) -> None:
        first_dir, second_dir = tmp_path / "run1", tmp_path / "run2"
        reference_plan(tmp_path, seed=11).write(first_dir)
        reference_plan(tmp_path, seed=11).write(second_dir)

        for name in ("sensors.geojson", "gateways.geojson", "site-report.md"):
            assert (first_dir / name).read_bytes() == (second_dir / name).read_bytes(), name

    def test_different_seed_changes_the_plan(self, tmp_path: Path) -> None:
        first = reference_plan(tmp_path, seed=1).sensors_geojson()
        second = reference_plan(tmp_path, seed=2).sensors_geojson()
        assert first != second


class TestReport:
    def test_reports_densities_relocations_and_seed(self, tmp_path: Path) -> None:
        plan = reference_plan(tmp_path, seed=11)
        report = plan.report_markdown()
        assert f"**Total nodes:** {len(plan.nodes)}" in report
        assert "Relocated nodes" in report
        assert "| Tier | Area (ha) | Nodes |" in report
        assert "seed: 11" in report

    def test_write_emits_the_three_artifacts(self, tmp_path: Path) -> None:
        out = tmp_path / "out"
        reference_plan(tmp_path).write(out)
        assert (out / "sensors.geojson").exists()
        assert (out / "gateways.geojson").exists()
        assert (out / "site-report.md").exists()
        # And the GeoJSON parses back.
        parsed = json.loads((out / "sensors.geojson").read_text(encoding="utf-8"))
        assert parsed["type"] == "FeatureCollection"


class TestValidation:
    def test_zero_nodes_is_a_clear_error(self, tmp_path: Path) -> None:
        terrain = make_terrain(tmp_path)
        # AOI completely outside the DEM: nothing can be placed.
        zones = ZoneSet.derive_default(box(10.0, 10.0, 10.05, 10.05))
        with pytest.raises(ValueError, match="zero nodes"):
            SitePlan.generate(terrain, zones, PlannerParams())
