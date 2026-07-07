"""Sensor placement over terrain and priority zones.

Turns a :class:`~pyrosense_sim.planner.terrain.TerrainModel` and a
:class:`~pyrosense_sim.planner.zones.ZoneSet` into concrete sensor
positions. The default strategy lays a hexagonal grid per tier
(densest packing of circular detection ranges), applies seeded jitter
so the deployment doesn't look artificially regular, and relocates —
never silently drops — candidates that land on terrain steeper than
the install threshold.

Design assumptions (reasoned defaults, not measured data):

- Effective detection radius per node ``r`` (default 125 m) gives a
  hex spacing ``d = r * sqrt(3)`` for full coverage; density targets
  per tier (T1: 1 node/4 ha, T2: 1/10 ha, T3: 1/25 ha) derive from the
  January 2024 fire case: ignition near trails and the wildland-urban
  interface, propagation in pine/eucalyptus stands.
- All randomness flows from one seeded ``random.Random`` so the same
  inputs and seed reproduce the exact same plan (byte-identical
  output; see ADR-0007).
"""

import random
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from math import ceil, sqrt
from typing import Protocol, runtime_checkable

from pyrosense_sim.planner.geo import meters_to_deg_lat, meters_to_deg_lon
from pyrosense_sim.planner.terrain import TerrainModel
from pyrosense_sim.planner.zones import Tier, ZoneSet

DEFAULT_DENSITY_HA: dict[Tier, float] = {1: 4.0, 2: 10.0, 3: 25.0}
"""Target density per tier as hectares per node."""

WIND_SENSOR_ONE_IN: dict[Tier, int] = {1: 10, 2: 20, 3: 20}
"""One in N nodes per tier carries a wind sensor (highest sites first)."""

_RELOCATION_RING_FRACTIONS = (0.25, 0.5)
_RELOCATION_DIRECTIONS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
_SQRT3 = sqrt(3.0)


@dataclass(frozen=True)
class PlannedNode:
    """A sensor site chosen by the planner (internal value object).

    ``gateway_id`` is ``None`` until gateway planning assigns one.
    """

    device_id: str
    lon: float
    lat: float
    tier: Tier
    zone_name: str
    elevation_m: float
    slope_deg: float
    has_wind_sensor: bool
    gateway_id: str | None = None


@dataclass(frozen=True)
class PlacementResult:
    """Outcome of a placement run, including relocation accounting."""

    nodes: tuple[PlannedNode, ...]
    relocated_count: int
    dropped_count: int


@runtime_checkable
class PlacementStrategy(Protocol):
    """Strategy interface: how sensor sites are chosen over the terrain."""

    def place(self, terrain: TerrainModel, zones: ZoneSet) -> PlacementResult:
        """Choose sensor sites for every zone.

        Args:
            terrain: Elevation/slope oracle in EPSG:4326.
            zones: Priority zones; every returned node belongs to one.

        Returns:
            The planned nodes plus relocation/drop counters.
        """
        ...


@dataclass(frozen=True)
class _Candidate:
    """A validated site before identity and wind assignment."""

    lon: float
    lat: float
    tier: Tier
    zone_name: str
    elevation_m: float
    slope_deg: float


class HexGridPlacement:
    """Hexagonal-grid placement with seeded jitter and slope relocation."""

    def __init__(
        self,
        *,
        densities_ha: dict[Tier, float] | None = None,
        detection_radius_m: float = 125.0,
        jitter_m: float = 25.0,
        max_slope_deg: float = 45.0,
        seed: int = 0,
    ) -> None:
        """Configure the strategy.

        Args:
            densities_ha: Target hectares per node, per tier. Defaults to
                :data:`DEFAULT_DENSITY_HA`.
            detection_radius_m: Effective detection radius of one node;
                documents the coverage assumption behind the densities.
            jitter_m: Max absolute jitter applied to each grid position on
                each axis, in meters.
            max_slope_deg: Sites steeper than this are relocated.
            seed: Seed for all randomness (determinism contract).

        Raises:
            ValueError: If any numeric parameter is not positive or any
                density is missing/non-positive.
        """
        densities = dict(DEFAULT_DENSITY_HA if densities_ha is None else densities_ha)
        for tier in (1, 2, 3):
            if densities.get(tier, 0.0) <= 0:
                msg = f"density for tier {tier} must be positive, got {densities.get(tier)!r}"
                raise ValueError(msg)
        if detection_radius_m <= 0 or max_slope_deg <= 0 or jitter_m < 0:
            msg = (
                "detection_radius_m and max_slope_deg must be positive and jitter_m "
                f"non-negative; got {detection_radius_m}, {max_slope_deg}, {jitter_m}"
            )
            raise ValueError(msg)
        self._densities_ha: dict[Tier, float] = densities
        self._detection_radius_m = detection_radius_m
        self._jitter_m = jitter_m
        self._max_slope_deg = max_slope_deg
        self._seed = seed

    def place(self, terrain: TerrainModel, zones: ZoneSet) -> PlacementResult:
        """Choose sensor sites for every zone (see :class:`PlacementStrategy`)."""
        rng = random.Random(self._seed)
        candidates: list[_Candidate] = []
        relocated = 0
        dropped = 0

        for zone in zones:
            spacing_m = self.spacing_m(zone.tier)
            for grid_lon, grid_lat in _hex_grid(zone.polygon.bounds, spacing_m):
                lon = grid_lon + meters_to_deg_lon(
                    rng.uniform(-self._jitter_m, self._jitter_m), grid_lat
                )
                lat = grid_lat + meters_to_deg_lat(rng.uniform(-self._jitter_m, self._jitter_m))
                if zones.tier_of(lon, lat) != zone.tier:
                    continue  # outside this zone (or claimed by a higher-priority one)

                sample = _sample_if_valid(terrain, lon, lat, self._max_slope_deg)
                if sample is None:
                    relocation = self._relocate(terrain, zones, zone.tier, lon, lat, spacing_m)
                    if relocation is None:
                        dropped += 1
                        continue
                    relocated += 1
                    lon, lat, sample = relocation
                candidates.append(
                    _Candidate(lon, lat, zone.tier, zone.zone_name, sample[0], sample[1])
                )

        return PlacementResult(
            nodes=_finalize(candidates),
            relocated_count=relocated,
            dropped_count=dropped,
        )

    def spacing_m(self, tier: Tier) -> float:
        """Hex spacing in meters that achieves the tier's target density.

        In a triangular lattice each node covers ``d^2 * sqrt(3)/2``, so
        ``d = sqrt(2 * area_per_node / sqrt(3))``.
        """
        area_m2 = self._densities_ha[tier] * 10_000.0
        return sqrt(2.0 * area_m2 / _SQRT3)

    def _relocate(
        self,
        terrain: TerrainModel,
        zones: ZoneSet,
        tier: Tier,
        lon: float,
        lat: float,
        spacing_m: float,
    ) -> tuple[float, float, tuple[float, float]] | None:
        """Find the nearest valid neighbour of an invalid site.

        Probes two rings (1/4 and 1/2 of the grid spacing) in eight fixed
        compass directions, nearest ring first — deterministic by
        construction. Returns ``(lon, lat, (elevation, slope))`` or
        ``None`` if every probe fails (caller counts it as dropped).
        """
        for fraction in _RELOCATION_RING_FRACTIONS:
            step_m = spacing_m * fraction
            for east, north in _RELOCATION_DIRECTIONS:
                cand_lon = lon + meters_to_deg_lon(step_m * east, lat)
                cand_lat = lat + meters_to_deg_lat(step_m * north)
                if zones.tier_of(cand_lon, cand_lat) != tier:
                    continue
                sample = _sample_if_valid(terrain, cand_lon, cand_lat, self._max_slope_deg)
                if sample is not None:
                    return cand_lon, cand_lat, sample
        return None


def _hex_grid(
    bounds: tuple[float, float, float, float], spacing_m: float
) -> Iterator[tuple[float, float]]:
    """Yield triangular-lattice points covering ``bounds``, row by row.

    Rows are ``spacing * sqrt(3)/2`` apart; odd rows shift half a spacing,
    forming the hexagonal packing. Yield order is deterministic
    (south to north, west to east).
    """
    min_lon, min_lat, max_lon, max_lat = bounds
    row_step_deg = meters_to_deg_lat(spacing_m * _SQRT3 / 2.0)
    lat = min_lat
    row = 0
    while lat <= max_lat:
        col_step_deg = meters_to_deg_lon(spacing_m, lat)
        lon = min_lon + (col_step_deg / 2.0 if row % 2 else 0.0)
        while lon <= max_lon:
            yield lon, lat
            lon += col_step_deg
        lat += row_step_deg
        row += 1


def _sample_if_valid(
    terrain: TerrainModel, lon: float, lat: float, max_slope_deg: float
) -> tuple[float, float] | None:
    """Return ``(elevation, slope)`` if the site is installable, else ``None``.

    Invalid means: outside the DEM, on/near nodata cells, or steeper than
    ``max_slope_deg``. All three make a site un-installable, so they share
    the same relocation path.
    """
    try:
        elevation = terrain.elevation_at(lon, lat)
        slope = terrain.slope_at(lon, lat)
    except ValueError:
        return None
    if slope > max_slope_deg:
        return None
    return elevation, slope


def _finalize(candidates: Sequence[_Candidate]) -> tuple[PlannedNode, ...]:
    """Assign device ids (per-tier sequence) and wind sensors (highest sites)."""
    wind_selected: set[int] = set()
    by_tier: dict[Tier, list[int]] = {1: [], 2: [], 3: []}
    for index, candidate in enumerate(candidates):
        by_tier[candidate.tier].append(index)
    for tier, indexes in by_tier.items():
        if not indexes:
            continue
        wind_count = ceil(len(indexes) / WIND_SENSOR_ONE_IN[tier])
        highest_first = sorted(indexes, key=lambda i: (-candidates[i].elevation_m, i))
        wind_selected.update(highest_first[:wind_count])

    nodes: list[PlannedNode] = []
    tier_sequence: dict[Tier, int] = {1: 0, 2: 0, 3: 0}
    for index, candidate in enumerate(candidates):
        tier_sequence[candidate.tier] += 1
        sequence = tier_sequence[candidate.tier]
        if sequence > 9999:  # pragma: no cover - defensive; contract allows 4 digits
            msg = f"tier {candidate.tier} exceeds 9999 devices; contract id format is full"
            raise ValueError(msg)
        nodes.append(
            PlannedNode(
                device_id=f"PYRO-T{candidate.tier}-{sequence:04d}",
                lon=candidate.lon,
                lat=candidate.lat,
                tier=candidate.tier,
                zone_name=candidate.zone_name,
                elevation_m=candidate.elevation_m,
                slope_deg=candidate.slope_deg,
                has_wind_sensor=index in wind_selected,
            )
        )
    return tuple(nodes)
