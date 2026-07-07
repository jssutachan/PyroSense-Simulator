"""Tests for Zone/ZoneSet: tier lookup, GeoJSON loading, default derivation."""

import json
from pathlib import Path

import pytest
from shapely.geometry import LineString, box, mapping

from pyrosense_sim.planner.zones import Zone, ZoneSet, _as_areal


def make_zoneset() -> ZoneSet:
    return ZoneSet(
        [
            Zone(polygon=box(0.0, 0.0, 1.0, 1.0), tier=1, zone_name="west"),
            Zone(polygon=box(1.0, 0.0, 2.0, 1.0), tier=2, zone_name="center"),
            Zone(polygon=box(0.5, 0.0, 1.5, 1.0), tier=3, zone_name="overlap"),
        ]
    )


class TestTierOf:
    def test_classifies_points_inside_each_zone(self) -> None:
        zones = make_zoneset()
        assert zones.tier_of(0.25, 0.5) == 1
        assert zones.tier_of(1.75, 0.5) == 2

    def test_outside_every_zone_returns_none(self) -> None:
        assert make_zoneset().tier_of(5.0, 5.0) is None

    def test_overlap_resolves_to_highest_priority(self) -> None:
        # (0.75, 0.5) lies in both the T1 and the T3 polygons.
        assert make_zoneset().tier_of(0.75, 0.5) == 1

    def test_boundary_counts_as_inside(self) -> None:
        assert make_zoneset().tier_of(0.0, 0.5) == 1


class TestFromGeojson:
    def write_collection(self, path: Path, features: list[dict[str, object]]) -> Path:
        path.write_text(
            json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8"
        )
        return path

    def feature(self, tier: object, **extra_properties: object) -> dict[str, object]:
        return {
            "type": "Feature",
            "geometry": mapping(box(0.0, 0.0, 1.0, 1.0)),
            "properties": {"tier": tier, **extra_properties},
        }

    def test_loads_zones_with_properties(self, tmp_path: Path) -> None:
        path = self.write_collection(
            tmp_path / "zones.geojson", [self.feature(1, zone_name="quebrada")]
        )
        zones = ZoneSet.from_geojson(path)
        assert len(zones.zones) == 1
        assert zones.zones[0].zone_name == "quebrada"
        assert zones.tier_of(0.5, 0.5) == 1

    def test_missing_zone_name_gets_a_default(self, tmp_path: Path) -> None:
        path = self.write_collection(tmp_path / "zones.geojson", [self.feature(2)])
        assert ZoneSet.from_geojson(path).zones[0].zone_name == "zone-0"

    def test_invalid_tier_is_rejected(self, tmp_path: Path) -> None:
        path = self.write_collection(tmp_path / "zones.geojson", [self.feature(7)])
        with pytest.raises(ValueError, match="'tier' must be 1, 2 or 3"):
            ZoneSet.from_geojson(path)

    def test_non_areal_geometry_is_rejected(self, tmp_path: Path) -> None:
        bad: dict[str, object] = {
            "type": "Feature",
            "geometry": mapping(LineString([(0, 0), (1, 1)])),
            "properties": {"tier": 1},
        }
        path = self.write_collection(tmp_path / "zones.geojson", [bad])
        with pytest.raises(ValueError, match="must be Polygon or MultiPolygon"):
            ZoneSet.from_geojson(path)


class TestDeriveDefault:
    # ~11 km square near the equator so the deg<->m approximation is exact.
    AOI = box(0.0, 0.0, 0.1, 0.1)
    T1_DEG = 400.0 / 111_320.0  # default buffer in degrees

    def test_western_strip_is_tier1_then_rings(self) -> None:
        zones = ZoneSet.derive_default(self.AOI)
        assert zones.tier_of(self.T1_DEG * 0.5, 0.05) == 1
        assert zones.tier_of(self.T1_DEG * 1.5, 0.05) == 2
        assert zones.tier_of(0.05, 0.05) == 3
        assert zones.tier_of(0.2, 0.05) is None

    def test_zone_names_document_the_derivation(self) -> None:
        names = {zone.zone_name for zone in ZoneSet.derive_default(self.AOI).zones}
        assert names == {"T1-derived", "T2-derived", "T3-derived"}

    def test_trails_become_tier1_corridors(self) -> None:
        trail = LineString([(0.05, 0.0), (0.05, 0.1)])  # north-south trail mid-AOI
        zones = ZoneSet.derive_default(self.AOI, trails=[trail])
        assert zones.tier_of(0.05 + self.T1_DEG * 0.5, 0.05) == 1
        assert zones.tier_of(0.05 + self.T1_DEG * 1.5, 0.05) == 2
        # Far from both the trail and the western edge: still T3.
        assert zones.tier_of(0.085, 0.05) == 3

    def test_custom_buffer_widens_tier1(self) -> None:
        wide = ZoneSet.derive_default(self.AOI, t1_buffer_m=800.0)
        point = (self.T1_DEG * 1.5, 0.05)  # T2 with the default buffer
        assert wide.tier_of(*point) == 1

    def test_non_positive_buffer_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="t1_buffer_m must be positive"):
            ZoneSet.derive_default(self.AOI, t1_buffer_m=0.0)


class TestContainerBehaviour:
    def test_len_and_iter(self) -> None:
        zones = make_zoneset()
        assert len(zones) == 3
        assert [zone.tier for zone in zones] == [1, 2, 3]

    def test_repr_summarizes_zones(self) -> None:
        assert repr(make_zoneset()) == "ZoneSet(3 zones: T1:west, T2:center, T3:overlap)"


def test_as_areal_rejects_non_areal_geometry() -> None:
    with pytest.raises(TypeError, match="expected areal geometry"):
        _as_areal(LineString([(0, 0), (1, 1)]))
