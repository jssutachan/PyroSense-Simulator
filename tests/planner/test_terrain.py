"""Tests for TerrainModel over synthetic DEMs (no external data files)."""

import math
from pathlib import Path

import numpy as np
import pytest
from rasterio.warp import transform_bounds

from pyrosense_sim.planner.terrain import TerrainModel
from tests.planner.synthetic_dem import DEFAULT_BOUNDS, write_dem

MIN_LON, MIN_LAT, MAX_LON, MAX_LAT = DEFAULT_BOUNDS
WIDTH, HEIGHT = 100, 50
XRES = (MAX_LON - MIN_LON) / WIDTH  # 0.001 deg
YRES = (MAX_LAT - MIN_LAT) / HEIGHT  # 0.002 deg


def lon_of_col(col: int) -> float:
    return MIN_LON + (col + 0.5) * XRES


def lat_of_row(row: int) -> float:
    return MAX_LAT - (row + 0.5) * YRES


def ramp_dem(tmp_path: Path) -> TerrainModel:
    """Elevation grows 10 m per column, west to east."""
    data = np.tile(10.0 * np.arange(WIDTH), (HEIGHT, 1)).astype(np.float64)
    return TerrainModel(write_dem(tmp_path / "ramp.tif", data))


class TestElevationAt:
    def test_returns_cell_value_at_known_points(self, tmp_path: Path) -> None:
        terrain = ramp_dem(tmp_path)
        assert terrain.elevation_at(lon_of_col(0), lat_of_row(10)) == 0.0
        assert terrain.elevation_at(lon_of_col(30), lat_of_row(25)) == 300.0
        assert terrain.elevation_at(lon_of_col(99), lat_of_row(49)) == 990.0

    def test_out_of_bounds_raises_clear_error(self, tmp_path: Path) -> None:
        terrain = ramp_dem(tmp_path)
        with pytest.raises(ValueError, match="outside the DEM extent"):
            terrain.elevation_at(-75.0, 4.55)
        with pytest.raises(ValueError, match="outside the DEM extent"):
            terrain.elevation_at(-74.05, 5.0)

    def test_nodata_cell_raises_clear_error(self, tmp_path: Path) -> None:
        data = np.full((HEIGHT, WIDTH), 100.0)
        data[10, 20] = -9999.0
        terrain = TerrainModel(write_dem(tmp_path / "holes.tif", data, nodata=-9999.0))
        with pytest.raises(ValueError, match="no data"):
            terrain.elevation_at(lon_of_col(20), lat_of_row(10))

    @pytest.mark.filterwarnings("ignore::rasterio.errors.NotGeoreferencedWarning")
    def test_missing_crs_is_rejected(self, tmp_path: Path) -> None:
        data = np.zeros((HEIGHT, WIDTH))
        path = write_dem(tmp_path / "nocrs.tif", data, crs=None)
        with pytest.raises(ValueError, match="no CRS"):
            TerrainModel(path)


class TestSlopeAt:
    def test_flat_terrain_has_zero_slope(self, tmp_path: Path) -> None:
        data = np.full((HEIGHT, WIDTH), 2800.0)
        terrain = TerrainModel(write_dem(tmp_path / "flat.tif", data))
        assert terrain.slope_at(lon_of_col(50), lat_of_row(25)) == pytest.approx(0.0)

    def test_corner_cells_use_replicated_borders(self, tmp_path: Path) -> None:
        data = np.full((HEIGHT, WIDTH), 2800.0)
        terrain = TerrainModel(write_dem(tmp_path / "flat.tif", data))
        assert terrain.slope_at(lon_of_col(0), lat_of_row(0)) == pytest.approx(0.0)
        assert terrain.slope_at(lon_of_col(WIDTH - 1), lat_of_row(HEIGHT - 1)) == pytest.approx(0.0)

    def test_ramp_slope_matches_physical_gradient(self, tmp_path: Path) -> None:
        terrain = ramp_dem(tmp_path)
        lat = lat_of_row(25)
        # 10 m of elevation gain per cell of XRES degrees of longitude.
        cell_width_m = XRES * 111_320.0 * math.cos(math.radians(lat))
        expected = math.degrees(math.atan(10.0 / cell_width_m))
        assert terrain.slope_at(lon_of_col(50), lat) == pytest.approx(expected, rel=0.01)
        assert expected > 4.0  # sanity: the ramp is clearly not flat

    def test_slope_grows_with_steeper_ramp(self, tmp_path: Path) -> None:
        gentle = ramp_dem(tmp_path)
        steep_data = np.tile(50.0 * np.arange(WIDTH), (HEIGHT, 1)).astype(np.float64)
        steep = TerrainModel(write_dem(tmp_path / "steep.tif", steep_data))
        point = (lon_of_col(50), lat_of_row(25))
        assert steep.slope_at(*point) > gentle.slope_at(*point)

    def test_nodata_neighbourhood_raises_clear_error(self, tmp_path: Path) -> None:
        data = np.full((HEIGHT, WIDTH), 100.0)
        data[10, 21] = -9999.0  # east neighbour of the queried cell
        terrain = TerrainModel(write_dem(tmp_path / "holes.tif", data, nodata=-9999.0))
        with pytest.raises(ValueError, match="slope is undefined"):
            terrain.slope_at(lon_of_col(20), lat_of_row(10))


class TestReprojection:
    def test_utm_raster_is_reprojected_to_wgs84(self, tmp_path: Path) -> None:
        # Same AOI expressed in UTM zone 18N (EPSG:32618), constant elevation.
        utm_bounds = transform_bounds("EPSG:4326", "EPSG:32618", *DEFAULT_BOUNDS)
        data = np.full((HEIGHT, WIDTH), 42.0)
        path = write_dem(tmp_path / "utm.tif", data, bounds=utm_bounds, crs="EPSG:32618")

        terrain = TerrainModel(path)

        min_lon, min_lat, max_lon, max_lat = terrain.bounds
        assert min_lon == pytest.approx(MIN_LON, abs=0.01)
        assert max_lat == pytest.approx(MAX_LAT, abs=0.01)
        center = ((min_lon + max_lon) / 2, (min_lat + max_lat) / 2)
        assert terrain.elevation_at(*center) == pytest.approx(42.0)
        assert terrain.slope_at(*center) == pytest.approx(0.0, abs=0.1)
