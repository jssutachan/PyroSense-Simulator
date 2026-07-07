"""Site plan assembly: nodes + gateways -> GeoJSON artifacts + report.

``SitePlan.generate`` orchestrates the placement strategy and the
gateway planner (both injectable, defaults provided) and ``write``
emits the three artifacts consumed downstream:

- ``sensores.geojson`` — input of the fleet engine (Path 5); its
  feature schema is stable from this path on.
- ``gateways.geojson`` — gateway metadata.
- ``site-report.md`` — human-readable summary for the deployment team.

Output is fully deterministic: no timestamps, sorted JSON keys and
fixed rounding, so the same inputs and seed produce byte-identical
files (tested). Coordinates round to 6 decimals (~0.11 m).
"""

import json
from dataclasses import dataclass, replace
from math import cos, radians
from pathlib import Path
from statistics import mean
from typing import cast

from pyrosense_sim.planner.gateways import Gateway, GatewayPlanner
from pyrosense_sim.planner.geo import M_PER_DEG_LAT, M_PER_DEG_LON_EQUATOR
from pyrosense_sim.planner.params import PlannerParams
from pyrosense_sim.planner.placement import HexGridPlacement, PlacementStrategy, PlannedNode
from pyrosense_sim.planner.terrain import TerrainModel
from pyrosense_sim.planner.zones import Tier, Zone, ZoneSet

SENSORS_FILENAME = "sensores.geojson"
GATEWAYS_FILENAME = "gateways.geojson"
REPORT_FILENAME = "site-report.md"


@dataclass(frozen=True)
class SitePlan:
    """A complete, ready-to-serialize deployment plan."""

    nodes: tuple[PlannedNode, ...]
    gateways: tuple[Gateway, ...]
    zones: ZoneSet
    params: PlannerParams
    relocated_count: int
    dropped_count: int

    @classmethod
    def generate(
        cls,
        terrain: TerrainModel,
        zones: ZoneSet,
        params: PlannerParams,
        *,
        strategy: PlacementStrategy | None = None,
        gateway_planner: GatewayPlanner | None = None,
    ) -> "SitePlan":
        """Run placement and gateway planning and assemble the plan.

        Args:
            terrain: Elevation/slope oracle.
            zones: Priority zones to cover.
            params: Validated planner configuration.
            strategy: Placement strategy override (defaults to
                :class:`HexGridPlacement` configured from ``params``).
            gateway_planner: Gateway planner override (defaults to one
                configured from ``params``).

        Returns:
            The assembled plan, with every node carrying its gateway id.

        Raises:
            ValueError: If placement produces zero nodes (e.g. the AOI
                lies outside the DEM or all terrain exceeds the slope
                threshold).
        """
        if strategy is None:
            strategy = HexGridPlacement(
                densities_ha=params.densities_ha,
                detection_radius_m=params.detection_radius_m,
                jitter_m=params.jitter_m,
                max_slope_deg=params.max_slope_deg,
                seed=params.seed,
            )
        placement = strategy.place(terrain, zones)
        if not placement.nodes:
            msg = (
                "placement produced zero nodes; check that the AOI overlaps the DEM "
                "and that max_slope_deg is not excluding all terrain"
            )
            raise ValueError(msg)
        if gateway_planner is None:
            gateway_planner = GatewayPlanner(
                capacity=params.gateway_capacity,
                snap_radius_m=params.gateway_snap_radius_m,
                seed=params.seed,
            )
        gateway_plan = gateway_planner.plan(placement.nodes, terrain)
        nodes = tuple(
            replace(node, gateway_id=gateway_plan.assignments[node.device_id])
            for node in placement.nodes
        )
        return cls(
            nodes=nodes,
            gateways=gateway_plan.gateways,
            zones=zones,
            params=params,
            relocated_count=placement.relocated_count,
            dropped_count=placement.dropped_count,
        )

    def sensors_geojson(self) -> dict[str, object]:
        """Build the sensors FeatureCollection (schema stable from Path 4 on)."""
        features = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(node.lon, 6), round(node.lat, 6)],
                },
                "properties": {
                    "device_id": node.device_id,
                    "tier": node.tier,
                    "zone_name": node.zone_name,
                    "elevation_m": round(node.elevation_m, 2),
                    "slope_deg": round(node.slope_deg, 2),
                    "gateway_id": node.gateway_id,
                    "has_wind_sensor": node.has_wind_sensor,
                },
            }
            for node in self.nodes
        ]
        return {"type": "FeatureCollection", "features": features}

    def gateways_geojson(self) -> dict[str, object]:
        """Build the gateways FeatureCollection."""
        features = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(gateway.lon, 6), round(gateway.lat, 6)],
                },
                "properties": {
                    "gateway_id": gateway.gateway_id,
                    "elevation_m": round(gateway.elevation_m, 2),
                    "assigned_nodes": sum(
                        1 for node in self.nodes if node.gateway_id == gateway.gateway_id
                    ),
                },
            }
            for gateway in self.gateways
        ]
        return {"type": "FeatureCollection", "features": features}

    def report_markdown(self) -> str:
        """Render the human-readable site report (deterministic, no timestamps)."""
        lines = [
            "# Site plan report",
            "",
            f"- **Total nodes:** {len(self.nodes)}",
            f"- **Gateways:** {len(self.gateways)} (capacity target: "
            f"{self.params.gateway_capacity} nodes/gateway)",
            f"- **Relocated nodes (slope/terrain):** {self.relocated_count}",
            f"- **Dropped candidates (no valid neighbour):** {self.dropped_count}",
            "",
            "## Density by tier",
            "",
            "| Tier | Area (ha) | Nodes | Achieved (ha/node) | Target (ha/node) |",
            "|---|---|---|---|---|",
        ]
        for tier in (1, 2, 3):
            tier_nodes = [node for node in self.nodes if node.tier == tier]
            area = sum(_zone_area_ha(zone) for zone in self.zones if zone.tier == tier)
            achieved = f"{area / len(tier_nodes):.1f}" if tier_nodes else "-"
            target = self.params.densities_ha[_as_tier(tier)]
            lines.append(
                f"| T{tier} | {area:.1f} | {len(tier_nodes)} | {achieved} | {target:.1f} |"
            )

        elevations = [node.elevation_m for node in self.nodes]
        slopes = [node.slope_deg for node in self.nodes]
        lines += [
            "",
            "## Terrain statistics",
            "",
            f"- **Elevation (m):** min {min(elevations):.1f} / "
            f"mean {mean(elevations):.1f} / max {max(elevations):.1f}",
            f"- **Slope (deg):** min {min(slopes):.2f} / "
            f"mean {mean(slopes):.2f} / max {max(slopes):.2f}",
            "",
            "## Parameters",
            "",
            f"- detection_radius_m: {self.params.detection_radius_m}",
            f"- densities_ha: T1={self.params.densities_ha[1]}, "
            f"T2={self.params.densities_ha[2]}, T3={self.params.densities_ha[3]}",
            f"- jitter_m: {self.params.jitter_m}",
            f"- max_slope_deg: {self.params.max_slope_deg}",
            f"- gateway_capacity: {self.params.gateway_capacity}",
            f"- gateway_snap_radius_m: {self.params.gateway_snap_radius_m}",
            f"- t1_buffer_m: {self.params.t1_buffer_m}",
            f"- **seed: {self.params.seed}** (same seed + inputs = identical plan)",
            "",
        ]
        return "\n".join(lines)

    def write(self, out_dir: Path) -> None:
        """Write the three plan artifacts into ``out_dir`` (created if needed).

        Args:
            out_dir: Destination directory for ``sensores.geojson``,
                ``gateways.geojson`` and ``site-report.md``.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        _write_json(out_dir / SENSORS_FILENAME, self.sensors_geojson())
        _write_json(out_dir / GATEWAYS_FILENAME, self.gateways_geojson())
        (out_dir / REPORT_FILENAME).write_text(self.report_markdown(), encoding="utf-8")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _zone_area_ha(zone: Zone) -> float:
    """Approximate a zone's area in hectares (deg^2 -> m^2 at its centroid latitude)."""
    lat_center = zone.polygon.centroid.y
    m2_per_deg2 = M_PER_DEG_LAT * M_PER_DEG_LON_EQUATOR * cos(radians(lat_center))
    return float(zone.polygon.area) * m2_per_deg2 / 10_000.0


def _as_tier(value: int) -> Tier:
    if value not in (1, 2, 3):  # pragma: no cover - internal invariant
        msg = f"invalid tier {value}"
        raise ValueError(msg)
    return cast(Tier, value)
