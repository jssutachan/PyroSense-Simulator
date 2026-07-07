"""Tests for GatewayPlanner: clustering, high-ground snap, full assignment."""

import re
from math import ceil
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import box

from pyrosense_sim.planner.gateways import GatewayPlanner
from pyrosense_sim.planner.placement import HexGridPlacement, PlacementResult
from pyrosense_sim.planner.terrain import TerrainModel
from pyrosense_sim.planner.zones import Zone, ZoneSet
from tests.planner.synthetic_dem import write_dem

WIDTH, HEIGHT = 100, 50


def make_terrain(tmp_path: Path) -> TerrainModel:
    data = np.tile(0.1 * np.arange(WIDTH), (HEIGHT, 1)).astype(np.float64)
    return TerrainModel(write_dem(tmp_path / "dem.tif", data))


def make_placement(tmp_path: Path) -> tuple[TerrainModel, PlacementResult]:
    terrain = make_terrain(tmp_path)
    zones = ZoneSet([Zone(box(-74.09, 4.51, -74.03, 4.57), tier=2, zone_name="t2")])
    return terrain, HexGridPlacement(seed=7).place(terrain, zones)


class TestPlan:
    def test_every_node_assigned_to_exactly_one_gateway(self, tmp_path: Path) -> None:
        terrain, placement = make_placement(tmp_path)
        plan = GatewayPlanner(capacity=10, seed=5).plan(placement.nodes, terrain)

        assert set(plan.assignments.keys()) == {node.device_id for node in placement.nodes}
        valid_ids = {gateway.gateway_id for gateway in plan.gateways}
        assert set(plan.assignments.values()) <= valid_ids

    def test_gateway_count_is_ceil_of_capacity(self, tmp_path: Path) -> None:
        terrain, placement = make_placement(tmp_path)
        capacity = 10
        plan = GatewayPlanner(capacity=capacity, seed=5).plan(placement.nodes, terrain)
        assert len(plan.gateways) == ceil(len(placement.nodes) / capacity)

    def test_gateway_ids_follow_contract_format(self, tmp_path: Path) -> None:
        terrain, placement = make_placement(tmp_path)
        plan = GatewayPlanner(capacity=10, seed=5).plan(placement.nodes, terrain)
        pattern = re.compile(r"^GW-\d{2,}$")
        assert all(pattern.match(gateway.gateway_id) for gateway in plan.gateways)
        assert plan.gateways[0].gateway_id == "GW-01"

    def test_deterministic_for_same_seed(self, tmp_path: Path) -> None:
        terrain, placement = make_placement(tmp_path)
        first = GatewayPlanner(capacity=10, seed=5).plan(placement.nodes, terrain)
        second = GatewayPlanner(capacity=10, seed=5).plan(placement.nodes, terrain)
        assert first == second

    def test_snaps_to_higher_ground(self, tmp_path: Path) -> None:
        # Elevation grows west to east: snapping must move gateways east
        # (higher) relative to their raw centroids, never lower than them.
        terrain, placement = make_placement(tmp_path)
        plan = GatewayPlanner(capacity=1000, seed=5).plan(placement.nodes, terrain)

        (gateway,) = plan.gateways
        centroid_lon = float(np.mean([node.lon for node in placement.nodes]))
        centroid_elevation = terrain.elevation_at(
            centroid_lon, float(np.mean([node.lat for node in placement.nodes]))
        )
        assert gateway.elevation_m >= centroid_elevation
        assert gateway.lon > centroid_lon


class TestValidation:
    def test_empty_nodes_rejected(self, tmp_path: Path) -> None:
        terrain = make_terrain(tmp_path)
        with pytest.raises(ValueError, match="empty node list"):
            GatewayPlanner().plan([], terrain)

    @pytest.mark.parametrize("kwargs", [{"capacity": 0}, {"snap_radius_m": -1.0}])
    def test_rejects_invalid_parameters(self, kwargs: dict[str, object]) -> None:
        with pytest.raises(ValueError, match="must be positive"):
            GatewayPlanner(**kwargs)  # type: ignore[arg-type]
