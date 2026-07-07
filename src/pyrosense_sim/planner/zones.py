"""Priority zones (tiers) for sensor placement.

A ``Zone`` is a polygon with a tier: T1 is highest priority (dense
sensor coverage), T3 lowest. Zones normally come from a GeoJSON the
user provides; when they don't, :meth:`ZoneSet.derive_default` builds
a documented simplification (see its docstring).

Coordinates are always EPSG:4326 lon/lat, matching the terrain model.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from shapely.geometry import LineString, MultiPolygon, Point, Polygon, shape
from shapely.geometry.base import BaseGeometry

Tier = Literal[1, 2, 3]

_M_PER_DEG_LON_AT_EQUATOR = 111_320.0


@dataclass(frozen=True)
class Zone:
    """A priority polygon. ``polygon`` may be multi-part after geometry ops."""

    polygon: Polygon | MultiPolygon
    tier: Tier
    zone_name: str


class ZoneSet:
    """Collection of zones with point-in-zone tier lookup."""

    def __init__(self, zones: Sequence[Zone]) -> None:
        self._zones = tuple(zones)

    @property
    def zones(self) -> tuple[Zone, ...]:
        return self._zones

    def tier_of(self, lon: float, lat: float) -> int | None:
        """Tier at (lon, lat), or None outside every zone.

        Where zones overlap, the highest priority (lowest tier number) wins.
        Points on a zone boundary count as inside.
        """
        point = Point(lon, lat)
        tiers = [zone.tier for zone in self._zones if zone.polygon.covers(point)]
        return min(tiers, default=None)

    @classmethod
    def from_geojson(cls, path: Path | str) -> "ZoneSet":
        """Load zones from a GeoJSON FeatureCollection.

        Each feature needs a Polygon/MultiPolygon geometry and properties
        ``tier`` (1|2|3) and ``zone_name``.
        """
        collection = json.loads(Path(path).read_text(encoding="utf-8"))
        zones: list[Zone] = []
        for feature in collection.get("features", []):
            geometry = shape(feature["geometry"])
            if not isinstance(geometry, Polygon | MultiPolygon):
                msg = f"zone geometry must be Polygon or MultiPolygon, got {geometry.geom_type}"
                raise ValueError(msg)
            properties = feature.get("properties") or {}
            tier = properties.get("tier")
            if tier not in (1, 2, 3):
                msg = f"zone property 'tier' must be 1, 2 or 3, got {tier!r}"
                raise ValueError(msg)
            zones.append(
                Zone(
                    polygon=geometry,
                    tier=tier,
                    zone_name=str(properties.get("zone_name", f"zone-{len(zones)}")),
                )
            )
        return cls(zones)

    @classmethod
    def derive_default(
        cls,
        aoi: Polygon,
        trails: Sequence[LineString] = (),
        t1_buffer_m: float = 400.0,
    ) -> "ZoneSet":
        """Derive zones when the user provides no tier polygons.

        Documented simplification (good enough for a first plan, not a
        fire-risk study):

        - **T1** = everything within ``t1_buffer_m`` of the AOI's western
          edge (the wildland-urban interface of the Cerros Orientales
          faces the city on the west) and of any provided trail lines
          (human ignition sources).
        - **T2** = a second ring, within ``2 * t1_buffer_m`` of the same
          features, excluding T1.
        - **T3** = the rest of the AOI.

        Buffers are computed in degrees with the equatorial meter/degree
        factor; at Bogota's latitude (~4.6 deg) the error is under 1%.
        """
        if t1_buffer_m <= 0:
            msg = f"t1_buffer_m must be positive, got {t1_buffer_m}"
            raise ValueError(msg)
        min_lon, min_lat, _max_lon, max_lat = aoi.bounds
        western_edge = LineString([(min_lon, min_lat), (min_lon, max_lat)])
        features = [western_edge, *trails]

        buffer_deg = t1_buffer_m / _M_PER_DEG_LON_AT_EQUATOR
        t2_outer = _buffer_union(features, 2 * buffer_deg)
        t1_geom = _as_areal(_buffer_union(features, buffer_deg).intersection(aoi))
        t2_geom = _as_areal(t2_outer.intersection(aoi).difference(t1_geom))
        t3_geom = _as_areal(aoi.difference(t2_outer))

        derived: list[tuple[Polygon | MultiPolygon, Tier, str]] = [
            (t1_geom, 1, "T1-derived"),
            (t2_geom, 2, "T2-derived"),
            (t3_geom, 3, "T3-derived"),
        ]
        zones = [
            Zone(polygon=geom, tier=tier, zone_name=name)
            for geom, tier, name in derived
            if not geom.is_empty
        ]
        return cls(zones)


def _buffer_union(features: Sequence[LineString], distance_deg: float) -> Polygon | MultiPolygon:
    merged: BaseGeometry = features[0].buffer(distance_deg)
    for feature in features[1:]:
        merged = merged.union(feature.buffer(distance_deg))
    return _as_areal(merged)


def _as_areal(geometry: BaseGeometry) -> Polygon | MultiPolygon:
    """Narrow a shapely result to areal geometry; empty results become empty polygons."""
    if isinstance(geometry, Polygon | MultiPolygon):
        return geometry
    if geometry.is_empty:  # pragma: no cover - defensive: ops on areal inputs stay areal
        return Polygon()
    msg = f"expected areal geometry, got {geometry.geom_type}"
    raise TypeError(msg)
