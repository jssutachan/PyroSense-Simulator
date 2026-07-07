# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/);
versionado alineado a hitos del proyecto. Una entrada por path completado.

## [Unreleased] — Consolidación P1–P3 (`chore/hardening-p1-p3`)

### Added
- Estrategia de ramas Git Flow simplificado (`main`/`develop`/`feature/*`) — ADR-0004.
- Documentación profesional: guía de arquitectura, guía del contrato de datos, 6 ADRs,
  informe de revisión de buenas prácticas, esta bitácora de cambios.
- Sitio de documentación con MkDocs Material + mkdocstrings (`mkdocs build`).
- Docstrings estilo Google en toda la API pública.
- `ndjson_line()`: fuente única del formato de línea NDJSON.
- `TerrainModel.__repr__`, `ZoneSet.__len__/__iter__/__repr__`.

### Changed
- `slope_at` delega la vecindad de celdas en `_neighbourhood()` (SRP a nivel de método).

## [0.3.0] — Path 3: site-planner, terreno y zonas — 2026-07-07

### Added
- `TerrainModel`: carga GeoTIFF (rasterio), normaliza a EPSG:4326 con reproyección
  bilinear, consultas `elevation_at`/`slope_at` con errores accionables.
- `Zone`/`ZoneSet`: polígonos de prioridad T1/T2/T3, lookup `tier_of`, carga GeoJSON
  y derivación por defecto documentada (borde occidental + senderos).
- Tests con DEMs 100 % sintéticos (rampa, plano, nodata, UTM).
- Política de warnings-como-errores en tests.

## [0.2.0] — Path 2: contrato de datos v1 + publishers — 2026-07-07

### Added
- `TelemetryPayload` v1 **congelado**: pydantic, `extra="forbid"`, frozen, `ts_device`
  UTC con sufijo `Z`, claves de viento nullable pero nunca omitidas — ADR-0002/0005.
- JSON Schema del contrato en `docs/payload-schema-v1.json` + test anti-drift.
- Interfaz `Publisher` (Protocol) y publishers `stdout` (NDJSON) y `file`
  (NDJSON con rotación por tamaño).
- Umbral de cobertura elevado a 90 (real: 100 %); mypy strict extendido a tests con
  plugin de pydantic.

## [0.1.0] — Path 1: andamiaje y tooling — 2026-07-07

### Added
- src layout (`src/pyrosense_sim/`), `pyproject.toml` (hatchling), grupos de
  dependencias, y tooling: ruff (lint+format), mypy strict, pytest-cov — ADR-0006.
- `.gitignore` (secretos, caches, binarios geoespaciales), `.env.example`,
  `data/README.md` con la guía de descarga del DEM (IGAC / Copernicus GLO-30).
- Smoke test del empaquetado.
