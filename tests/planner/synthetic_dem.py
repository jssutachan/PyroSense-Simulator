"""Helper to write small synthetic DEM GeoTIFFs for tests (no external data)."""

from pathlib import Path

import numpy as np
import numpy.typing as npt
import rasterio
from rasterio.transform import from_bounds

# A ~11 km x 11 km box roughly over the Cerros Orientales.
DEFAULT_BOUNDS = (-74.10, 4.50, -74.00, 4.60)


def write_dem(
    path: Path,
    data: npt.NDArray[np.float64],
    *,
    bounds: tuple[float, float, float, float] = DEFAULT_BOUNDS,
    crs: str | None = "EPSG:4326",
    nodata: float | None = None,
) -> Path:
    """Write a single-band float64 GeoTIFF covering ``bounds`` and return its path."""
    height, width = data.shape
    transform = from_bounds(*bounds, width, height)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float64",
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(data, 1)
    return path
