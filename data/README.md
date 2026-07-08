# Geospatial data — Cerros Orientales DEM

This directory holds the Digital Elevation Model (DEM) consumed by the
**site-planner**. Heavy binaries (`.tif`, `.zip`) are **never committed**
(see `.gitignore`); every developer downloads them locally following these steps.

## Area of interest

Bogotá's Cerros Orientales (eastern hills), approximately:

| Bound | Value |
|--------|-------|
| Latitude  | 4.45° N to 4.80° N |
| Longitude | 74.15° W to 73.95° W |

**Expected format:** GeoTIFF (`.tif`), a single file, in a geographic CRS
(EPSG:4326) or a projected one (MAGNA-SIRGAS / UTM); the planner reprojects
when needed. Place it here as `data/dem_cerros_orientales.tif`.

## Option A — IGAC "Colombia en Mapas" (official Colombian source)

1. Go to <https://www.colombiaenmapas.gov.co>.
2. Search for **"Modelo Digital de Elevación"** (Digital Elevation Model),
   or browse the *Relieve* (relief) category.
3. Select the DEM product available for Cundinamarca / Bogotá D.C.
   (IGAC publishes DEMs derived from its surveys, typically at 12.5 m or 30 m).
4. Use the area-download tool: draw or enter the bounding box from the
   table above.
5. Download in **GeoTIFF** format. If the portal delivers a `.zip`,
   extract it and keep only the `.tif`.
6. Rename it to `dem_cerros_orientales.tif` and place it in this directory.

> Note: the IGAC portal requires free registration for downloads and its
> catalog changes frequently. If the product is missing or the download
> fails, use Option B.

## Option B — Copernicus GLO-30 via OpenTopography (global alternative, 30 m)

1. Go to <https://portal.opentopography.org> and create a free account
   (required to download global datasets).
2. Navigate to **Data > Global & Regional DEMs** and choose
   **Copernicus GLO-30** (Copernicus DEM 30 m).
3. Under *Select Coordinates*, enter the bounding box:
   - Xmin (lon): `-74.15` — Xmax (lon): `-73.95`
   - Ymin (lat): `4.45` — Ymax (lat): `4.80`
4. Output format: **GeoTIFF**. Launch the job and download the result
   (a few tens of MB for this area).
5. Rename it to `dem_cerros_orientales.tif` and place it in this directory.

## Quick verification

With the project environment active:

```bash
python -c "import rasterio; d = rasterio.open('data/dem_cerros_orientales.tif'); print(d.crs, d.shape, d.bounds)"
```

It should print the CRS, the raster dimensions, and bounds containing the
area of interest. If `rasterio` cannot open the file, check that it is a
GeoTIFF and not a portal-specific proprietary format.
