"""Tests for HexGridPlacement over synthetic terrain."""

import re
from math import ceil, cos, radians
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import box

from pyrosense_sim.planner.geo import M_PER_DEG_LAT, M_PER_DEG_LON_EQUATOR
from pyrosense_sim.planner.placement import HexGridPlacement, PlacementStrategy
from pyrosense_sim.planner.terrain import TerrainModel
from pyrosense_sim.planner.zones import Zone, ZoneSet
from tests.planner.synthetic_dem import write_dem

WIDTH, HEIGHT = 100, 50


def flat_terrain(tmp_path: Path, name: str = "flat.tif") -> TerrainModel:
    """Gentle west-east ramp: negligible slope, but distinct elevations."""
    data = np.tile(0.1 * np.arange(WIDTH), (HEIGHT, 1)).astype(np.float64)
    return TerrainModel(write_dem(tmp_path / name, data))


def area_ha(zone_box: tuple[float, float, float, float]) -> float:
    min_lon, min_lat, max_lon, max_lat = zone_box
    lat_c = (min_lat + max_lat) / 2
    width_m = (max_lon - min_lon) * M_PER_DEG_LON_EQUATOR * cos(radians(lat_c))
    height_m = (max_lat - min_lat) * M_PER_DEG_LAT
    return width_m * height_m / 10_000.0


class TestDensities:
    @pytest.mark.parametrize(("tier", "ha_per_node"), [(1, 4.0), (2, 10.0), (3, 25.0)])
    def test_achieved_density_within_tolerance(
        self, tmp_path: Path, tier: int, ha_per_node: float
    ) -> None:
        bounds = (-74.09, 4.51, -74.03, 4.57)  # ~6.6 km x 6.6 km inside the DEM
        zones = ZoneSet([Zone(box(*bounds), tier=tier, zone_name=f"t{tier}")])  # type: ignore[arg-type]
        result = HexGridPlacement(seed=7).place(flat_terrain(tmp_path), zones)

        expected = area_ha(bounds) / ha_per_node
        assert result.nodes, "placement produced no nodes"
        assert expected * 0.7 <= len(result.nodes) <= expected * 1.3
        assert result.dropped_count == 0

    def test_device_ids_follow_contract_format(self, tmp_path: Path) -> None:
        bounds = (-74.09, 4.51, -74.05, 4.55)
        zones = ZoneSet([Zone(box(*bounds), tier=1, zone_name="t1")])
        result = HexGridPlacement(seed=7).place(flat_terrain(tmp_path), zones)

        pattern = re.compile(r"^PYRO-T1-\d{4}$")
        assert all(pattern.match(node.device_id) for node in result.nodes)
        # Sequential and unique per tier.
        assert len({node.device_id for node in result.nodes}) == len(result.nodes)
        assert result.nodes[0].device_id == "PYRO-T1-0001"


class TestSlopeRelocation:
    def make_spiked_terrain(self, tmp_path: Path) -> TerrainModel:
        """Flat terrain with one impossible-slope column spike."""
        data = np.zeros((HEIGHT, WIDTH), dtype=np.float64)
        data[:, 45] = 10_000.0  # ~89 deg slope on and around the spike
        return TerrainModel(write_dem(tmp_path / "spike.tif", data))

    def test_steep_sites_are_relocated_not_dropped(self, tmp_path: Path) -> None:
        terrain = self.make_spiked_terrain(tmp_path)
        zones = ZoneSet([Zone(box(-74.08, 4.51, -74.04, 4.59), tier=2, zone_name="t2")])
        result = HexGridPlacement(seed=3, max_slope_deg=45.0).place(terrain, zones)

        assert result.relocated_count > 0
        assert all(node.slope_deg <= 45.0 for node in result.nodes)

    def test_impossible_terrain_drops_with_accounting(self, tmp_path: Path) -> None:
        # A ~89.9 deg ramp everywhere: no valid neighbour exists anywhere.
        # (An alternating-columns "teeth" pattern would NOT work here: central
        # differences alias it to zero slope because east and west neighbours
        # are equal on every cell.)
        data = np.tile(100_000.0 * np.arange(WIDTH), (HEIGHT, 1)).astype(np.float64)
        terrain = TerrainModel(write_dem(tmp_path / "steep_ramp.tif", data))
        zones = ZoneSet([Zone(box(-74.08, 4.51, -74.04, 4.59), tier=2, zone_name="t2")])
        result = HexGridPlacement(seed=3).place(terrain, zones)

        assert result.nodes == ()
        assert result.dropped_count > 0


class TestDeterminism:
    def test_same_seed_same_nodes(self, tmp_path: Path) -> None:
        terrain = flat_terrain(tmp_path)
        zones = ZoneSet([Zone(box(-74.09, 4.51, -74.04, 4.56), tier=2, zone_name="t2")])
        first = HexGridPlacement(seed=42).place(terrain, zones)
        second = HexGridPlacement(seed=42).place(terrain, zones)
        assert first == second

    def test_different_seed_different_jitter(self, tmp_path: Path) -> None:
        terrain = flat_terrain(tmp_path)
        zones = ZoneSet([Zone(box(-74.09, 4.51, -74.04, 4.56), tier=2, zone_name="t2")])
        first = HexGridPlacement(seed=1).place(terrain, zones)
        second = HexGridPlacement(seed=2).place(terrain, zones)
        assert first != second


class TestWindSensors:
    def test_ratio_and_highest_elevation_selection(self, tmp_path: Path) -> None:
        terrain = flat_terrain(tmp_path)  # elevation grows west to east
        zones = ZoneSet([Zone(box(-74.09, 4.51, -74.03, 4.57), tier=1, zone_name="t1")])
        result = HexGridPlacement(seed=7).place(terrain, zones)

        with_wind = [node for node in result.nodes if node.has_wind_sensor]
        assert len(with_wind) == ceil(len(result.nodes) / 10)
        # The chosen ones are exactly the highest sites.
        min_wind_elevation = min(node.elevation_m for node in with_wind)
        without_wind = [node for node in result.nodes if not node.has_wind_sensor]
        assert all(node.elevation_m <= min_wind_elevation for node in without_wind)

    def test_one_in_twenty_for_lower_tiers(self, tmp_path: Path) -> None:
        terrain = flat_terrain(tmp_path)
        zones = ZoneSet([Zone(box(-74.09, 4.51, -74.03, 4.57), tier=3, zone_name="t3")])
        result = HexGridPlacement(seed=7).place(terrain, zones)
        with_wind = [node for node in result.nodes if node.has_wind_sensor]
        assert len(with_wind) == ceil(len(result.nodes) / 20)


class TestValidation:
    def test_conforms_to_strategy_protocol(self) -> None:
        strategy: PlacementStrategy = HexGridPlacement()
        assert isinstance(strategy, PlacementStrategy)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"densities_ha": {1: 4.0, 2: 0.0, 3: 25.0}},
            {"detection_radius_m": 0.0},
            {"max_slope_deg": -1.0},
            {"jitter_m": -5.0},
        ],
    )
    def test_rejects_invalid_parameters(self, kwargs: dict[str, object]) -> None:
        with pytest.raises(ValueError, match="must be"):
            HexGridPlacement(**kwargs)  # type: ignore[arg-type]

    def test_spacing_matches_design_table(self) -> None:
        strategy = HexGridPlacement()
        assert strategy.spacing_m(1) == pytest.approx(215.0, abs=5.0)  # 200-220 m
        assert strategy.spacing_m(2) == pytest.approx(340.0, abs=5.0)
        assert strategy.spacing_m(3) == pytest.approx(537.0, abs=5.0)
