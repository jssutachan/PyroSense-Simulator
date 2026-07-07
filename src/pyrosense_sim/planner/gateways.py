"""Gateway planning: cluster sensor nodes and pick elevated gateway sites.

Gateways here are **pure metadata** for the fleet simulator: which
``gateway_id`` each node reports through. No radio propagation is
simulated (see ADR-0008) — the only physical nod is snapping each
gateway to the highest ground within a small radius, since real LoRa
gateways favour high sites.

Clustering is a small seeded k-means implemented on numpy directly:
pulling in scikit-learn for 30 lines would cost far more than it buys.
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from math import ceil

import numpy as np
import numpy.typing as npt

from pyrosense_sim.planner.geo import meters_to_deg_lat, meters_to_deg_lon
from pyrosense_sim.planner.placement import PlannedNode
from pyrosense_sim.planner.terrain import TerrainModel

_SNAP_GRID_STEP_M = 50.0
_KMEANS_MAX_ITERATIONS = 100


@dataclass(frozen=True)
class Gateway:
    """A planned gateway site (metadata only, no radio model)."""

    gateway_id: str
    lon: float
    lat: float
    elevation_m: float


@dataclass(frozen=True)
class GatewayPlan:
    """Gateways plus the node-to-gateway assignment."""

    gateways: tuple[Gateway, ...]
    assignments: dict[str, str]
    """Maps ``device_id`` to ``gateway_id``; every node appears exactly once."""


class GatewayPlanner:
    """Plan gateway sites by clustering node positions."""

    def __init__(
        self,
        *,
        capacity: int = 60,
        snap_radius_m: float = 200.0,
        seed: int = 0,
    ) -> None:
        """Configure the planner.

        Args:
            capacity: Nodes per gateway used to size the cluster count
                (``ceil(n / capacity)``). Nearest-gateway assignment may
                exceed it slightly; capacity is a sizing target, not a
                hard limit.
            snap_radius_m: Radius around each centroid searched for the
                highest ground.
            seed: Seed for the k-means initialization (determinism).

        Raises:
            ValueError: If ``capacity`` or ``snap_radius_m`` is not positive.
        """
        if capacity <= 0 or snap_radius_m <= 0:
            msg = f"capacity and snap_radius_m must be positive, got {capacity}, {snap_radius_m}"
            raise ValueError(msg)
        self._capacity = capacity
        self._snap_radius_m = snap_radius_m
        self._seed = seed

    def plan(self, nodes: Sequence[PlannedNode], terrain: TerrainModel) -> GatewayPlan:
        """Cluster nodes, snap gateways to high ground and assign every node.

        Args:
            nodes: Planned sensor nodes (at least one).
            terrain: Elevation oracle used for the high-ground snap.

        Returns:
            The gateways (``GW-01``, ``GW-02``, ...) and a complete
            device-to-gateway assignment.

        Raises:
            ValueError: If ``nodes`` is empty.
        """
        if not nodes:
            msg = "cannot plan gateways for an empty node list"
            raise ValueError(msg)
        positions = np.array([[node.lon, node.lat] for node in nodes], dtype=np.float64)
        cluster_count = ceil(len(nodes) / self._capacity)
        centroids = _kmeans(positions, cluster_count, random.Random(self._seed))

        gateways = tuple(
            self._gateway_at(index, lon=float(center[0]), lat=float(center[1]), terrain=terrain)
            for index, center in enumerate(centroids)
        )

        gateway_positions = np.array([[gw.lon, gw.lat] for gw in gateways], dtype=np.float64)
        distances = ((positions[:, None, :] - gateway_positions[None, :, :]) ** 2).sum(axis=2)
        nearest = distances.argmin(axis=1)
        assignments = {
            node.device_id: gateways[int(index)].gateway_id
            for node, index in zip(nodes, nearest, strict=True)
        }
        return GatewayPlan(gateways=gateways, assignments=assignments)

    def _gateway_at(self, index: int, *, lon: float, lat: float, terrain: TerrainModel) -> Gateway:
        """Build a gateway at the highest valid ground near a centroid."""
        best_lon, best_lat, best_elevation = lon, lat, _elevation_or_none(terrain, lon, lat)
        steps = int(self._snap_radius_m // _SNAP_GRID_STEP_M)
        for row in range(-steps, steps + 1):
            for col in range(-steps, steps + 1):
                offset_north_m = row * _SNAP_GRID_STEP_M
                offset_east_m = col * _SNAP_GRID_STEP_M
                if offset_north_m**2 + offset_east_m**2 > self._snap_radius_m**2:
                    continue
                cand_lon = lon + meters_to_deg_lon(offset_east_m, lat)
                cand_lat = lat + meters_to_deg_lat(offset_north_m)
                elevation = _elevation_or_none(terrain, cand_lon, cand_lat)
                if elevation is not None and (best_elevation is None or elevation > best_elevation):
                    best_lon, best_lat, best_elevation = cand_lon, cand_lat, elevation
        return Gateway(
            gateway_id=f"GW-{index + 1:02d}",
            lon=best_lon,
            lat=best_lat,
            elevation_m=best_elevation if best_elevation is not None else 0.0,
        )


def _elevation_or_none(terrain: TerrainModel, lon: float, lat: float) -> float | None:
    try:
        return terrain.elevation_at(lon, lat)
    except ValueError:
        return None


def _kmeans(
    points: npt.NDArray[np.float64], cluster_count: int, rng: random.Random
) -> npt.NDArray[np.float64]:
    """Seeded Lloyd's k-means; deterministic for a given rng state.

    Empty clusters keep their previous centroid, which is enough for the
    small, well-spread point sets the planner produces.
    """
    if cluster_count >= len(points):
        return points.copy()
    initial = sorted(rng.sample(range(len(points)), cluster_count))
    centroids = points[initial].copy()
    for _ in range(_KMEANS_MAX_ITERATIONS):
        distances = ((points[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        labels = distances.argmin(axis=1)
        updated = centroids.copy()
        for cluster in range(cluster_count):
            members = points[labels == cluster]
            if len(members):
                updated[cluster] = members.mean(axis=0)
        if np.allclose(updated, centroids):
            break
        centroids = updated
    return centroids
