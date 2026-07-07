# Datos geoespaciales — DEM de los Cerros Orientales

Este directorio aloja el Modelo Digital de Elevación (DEM) que consume el
**site-planner**. Los binarios pesados (`.tif`, `.zip`) **no se versionan en git**
(ver `.gitignore`); cada desarrollador los descarga localmente siguiendo estos pasos.

## Área de interés

Cerros Orientales de Bogotá, aproximadamente:

| Límite | Valor |
|--------|-------|
| Latitud  | 4.45° N a 4.80° N |
| Longitud | 74.15° W a 73.95° W |

**Formato esperado:** GeoTIFF (`.tif`), un solo archivo, CRS geográfico
(EPSG:4326) o proyectado (MAGNA-SIRGAS / UTM); el planner reproyecta si hace falta.
Colócalo aquí como `data/dem_cerros_orientales.tif`.

## Opción A — IGAC "Colombia en Mapas" (fuente oficial colombiana)

1. Entra a <https://www.colombiaenmapas.gov.co>.
2. En el buscador escribe **"Modelo Digital de Elevación"** (o navega por la
   categoría *Relieve*).
3. Selecciona el producto DEM disponible para Cundinamarca / Bogotá D.C.
   (el IGAC publica DEM derivados de sus levantamientos, típicamente a 12.5 m o 30 m).
4. Usa la herramienta de descarga por área: dibuja o introduce el bounding box
   de la tabla de arriba.
5. Descarga en formato **GeoTIFF**. Si el portal entrega un `.zip`, descomprímelo
   y conserva solo el `.tif`.
6. Renombra a `dem_cerros_orientales.tif` y déjalo en este directorio.

> Nota: el portal del IGAC requiere registro gratuito para descargas y su catálogo
> cambia con frecuencia. Si el producto no aparece o la descarga falla, usa la Opción B.

## Opción B — Copernicus GLO-30 vía OpenTopography (alternativa global, 30 m)

1. Entra a <https://portal.opentopography.org> y crea una cuenta gratuita
   (requerida para descargar datasets globales).
2. Ve a **Data > Global & Regional DEMs** y elige
   **Copernicus GLO-30** (Copernicus DEM 30 m).
3. En *Select Coordinates*, introduce el bounding box:
   - Xmin (lon): `-74.15` — Xmax (lon): `-73.95`
   - Ymin (lat): `4.45` — Ymax (lat): `4.80`
4. Formato de salida: **GeoTIFF**. Lanza el job y descarga el resultado
   (para esta área son unas decenas de MB).
5. Renombra a `dem_cerros_orientales.tif` y déjalo en este directorio.

## Verificación rápida

Con el entorno del proyecto activo:

```bash
python -c "import rasterio; d = rasterio.open('data/dem_cerros_orientales.tif'); print(d.crs, d.shape, d.bounds)"
```

Debe imprimir el CRS, las dimensiones del raster y unos bounds que contengan el
área de interés. Si `rasterio` no puede abrir el archivo, revisa que sea un
GeoTIFF y no un formato propietario del portal.
