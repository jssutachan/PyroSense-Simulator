"""Terrain model backed by a DEM GeoTIFF.

Loads a digital elevation model with rasterio, normalizes it to
EPSG:4326 (WGS84 lon/lat) and answers point queries: elevation and
local slope. The raster resolution is read from the file itself; no
fixed cell size is assumed.

Slope method: central finite differences over the 4-connected cell
neighbourhood (replicating border cells at the raster edge). The
horizontal cell sizes are converted from degrees to meters using the
local latitude (lon degrees shrink by cos(lat)), then::

    slope_deg = degrees(atan(hypot(dz/dx, dz/dy)))

This is the classic Zevenbergen-Thorne 2nd-order estimate; adequate
for sensor placement, not for hydrological modelling.
"""

from math import atan, cos, degrees, hypot, isnan, radians
from pathlib import Path

import numpy as np
import numpy.typing as npt
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.transform import Affine, array_bounds, rowcol
from rasterio.warp import calculate_default_transform, reproject

from pyrosense_sim.planner.geo import M_PER_DEG_LAT, M_PER_DEG_LON_EQUATOR

_WGS84 = CRS.from_epsg(4326)


class TerrainModel:
    """In-memory DEM in EPSG:4326 with point queries for elevation and slope.

    Example:
        >>> terrain = TerrainModel("data/dem_cerros_orientales.tif")  # doctest: +SKIP
        >>> terrain.elevation_at(-74.04, 4.61)  # doctest: +SKIP
        3050.0
    """

    def __init__(self, dem_path: Path | str) -> None:
        """Load a DEM GeoTIFF fully into memory, normalizing to EPSG:4326.

        Args:
            dem_path: Path to a single-band, georeferenced GeoTIFF. Rasters
                in other CRS are reprojected (bilinear) at load time.

        Raises:
            ValueError: If the raster has no CRS.
            rasterio.errors.RasterioIOError: If the file cannot be opened.
        """
        with rasterio.open(dem_path) as src:
            if src.crs is None:
                msg = f"DEM {dem_path} has no CRS; a georeferenced GeoTIFF is required"
                raise ValueError(msg)
            if src.crs == _WGS84:
                data = src.read(1).astype(np.float64)
                transform: Affine = src.transform
            else:
                data, transform = self._reproject_to_wgs84(src)
            if src.nodata is not None:
                data[data == float(src.nodata)] = np.nan
        self._data: npt.NDArray[np.float64] = data
        self._transform = transform
        rows, cols = data.shape
        self._bounds: tuple[float, float, float, float] = array_bounds(rows, cols, transform)

    @staticmethod
    def _reproject_to_wgs84(
        src: rasterio.DatasetReader,
    ) -> tuple[npt.NDArray[np.float64], Affine]:
        transform, width, height = calculate_default_transform(
            src.crs, _WGS84, src.width, src.height, *src.bounds
        )
        destination = np.full((int(height), int(width)), np.nan, dtype=np.float64)
        reproject(
            source=rasterio.band(src, 1),
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=src.nodata,
            dst_transform=transform,
            dst_crs=_WGS84,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
        return destination, transform

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """DEM extent as (min_lon, min_lat, max_lon, max_lat) in EPSG:4326."""
        return self._bounds

    @property
    def elevation_grid(self) -> npt.NDArray[np.float64]:
        """The raw elevation raster (row 0 = north). Treat as read-only."""
        return self._data

    def elevation_at(self, lon: float, lat: float) -> float:
        """Sample the elevation at a point.

        Args:
            lon: Longitude in decimal degrees (EPSG:4326).
            lat: Latitude in decimal degrees (EPSG:4326).

        Returns:
            Elevation in meters at the DEM cell containing the point.

        Raises:
            ValueError: If the point falls outside the DEM extent (the
                message includes the valid extent) or on a nodata cell.
        """
        row, col = self._cell_for(lon, lat)
        value = float(self._data[row, col])
        if isnan(value):
            msg = f"DEM has no data at ({lon}, {lat})"
            raise ValueError(msg)
        return value

    def slope_at(self, lon: float, lat: float) -> float:
        """Compute the local slope at a point.

        Uses central finite differences over the 4-connected cell
        neighbourhood; see the module docstring for the full method.

        Args:
            lon: Longitude in decimal degrees (EPSG:4326).
            lat: Latitude in decimal degrees (EPSG:4326).

        Returns:
            Slope in degrees: 0.0 is flat, 45.0 means 1 m of rise per
            meter of horizontal distance.

        Raises:
            ValueError: If the point falls outside the DEM extent or its
                neighbourhood contains nodata cells.
        """
        row, col = self._cell_for(lon, lat)
        north, south, west, east = self._neighbourhood(row, col)
        if any(isnan(v) for v in (north, south, east, west)):
            msg = f"DEM has nodata cells around ({lon}, {lat}); slope is undefined there"
            raise ValueError(msg)

        xres_deg, yres_deg = abs(self._transform.a), abs(self._transform.e)
        xres_m = xres_deg * M_PER_DEG_LON_EQUATOR * cos(radians(lat))
        yres_m = yres_deg * M_PER_DEG_LAT
        dz_dx = (east - west) / (2.0 * xres_m)
        dz_dy = (south - north) / (2.0 * yres_m)
        return degrees(atan(hypot(dz_dx, dz_dy)))

    def __repr__(self) -> str:
        rows, cols = self._data.shape
        min_lon, min_lat, max_lon, max_lat = self._bounds
        return (
            f"TerrainModel({rows}x{cols} cells, "
            f"lon [{min_lon:.4f}, {max_lon:.4f}], lat [{min_lat:.4f}, {max_lat:.4f}])"
        )

    def _neighbourhood(self, row: int, col: int) -> tuple[float, float, float, float]:
        """Return (north, south, west, east) elevations, replicating borders at edges."""
        rows, cols = self._data.shape
        return (
            float(self._data[max(row - 1, 0), col]),
            float(self._data[min(row + 1, rows - 1), col]),
            float(self._data[row, max(col - 1, 0)]),
            float(self._data[row, min(col + 1, cols - 1)]),
        )

    def _cell_for(self, lon: float, lat: float) -> tuple[int, int]:
        row, col = rowcol(self._transform, lon, lat)
        row_i, col_i = int(row), int(col)
        rows, cols = self._data.shape
        if not (0 <= row_i < rows and 0 <= col_i < cols):
            min_lon, min_lat, max_lon, max_lat = self._bounds
            msg = (
                f"point ({lon}, {lat}) is outside the DEM extent "
                f"lon [{min_lon:.6f}, {max_lon:.6f}], lat [{min_lat:.6f}, {max_lat:.6f}]"
            )
            raise ValueError(msg)
        return row_i, col_i
