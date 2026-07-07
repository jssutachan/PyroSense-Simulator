# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/);
versionado alineado a hitos del proyecto. Una entrada por path completado.

## [0.6.0] — Path 6: eventos de fuego + inyección de fallos — 2026-07-07

### Added
- `FireEvent`: fuego paramétrico (círculo con crecimiento radial, deriva por
  viento, ramp-in smoothstep, halo de decaimiento) que perturba la línea base en
  `EnvironmentModel.conditions_at` — interpolación, no física (ADR-0011).
- `FaultInjector`: decorador componible del `Publisher` (ADR-0012) —
  `node_dropout`, `burst_reconnect` (backlog con `ts_device` originales y `seq`
  consecutivos), `duplicates` QoS 1, `out_of_order`, `battery_decay`;
  `SensorNode` intacto.
- Escenarios `replay_enero_2024.yaml` (firma del incendio real, comentado) y
  `fallos.yaml` (los cinco fallos, componible sobre cualquier escenario).
- Bloques `fires:`/`faults:` en el YAML de escenario, validación estricta;
  `geo.distance_m` compartido.

## [0.5.0] — Path 5: motor de flota baseline — 2026-07-07

### Added
- `fleet/config.py`: escenarios YAML validados con pydantic estricto (frontera de
  usuario); escenarios `baseline.yaml` y `temporada_seca.yaml` (El Niño, sin fuego).
- `EnvironmentModel`: verdad de terreno pura — ciclo diurno sinusoidal, lapse rate
  −6.5 °C/km, humedad anticorrelacionada; hook para eventos de fuego (P6) — ADR-0009.
- `SensorNode`: RNG propio por nodo (`seed:device_id`), `seq` monótono, batería con
  drenaje temporal, `status` por umbrales, cadencia adaptativa 300 s → 30 s.
- `Scheduler`: heap determinista (desempate por device_id) con reloj simulado y
  `--speed`; sleep inyectable.
- `FleetOrchestrator`: carga `sensores.geojson` validando propiedades, compone todo
  vía DIP, SIGINT cierra limpio con resumen (emitidos, por status, duración sim/real).
- CLI `fleet-sim run` (typer): stdout = datos NDJSON, stderr = logs — ADR-0010;
  corre íntegramente sin credenciales AWS.

## [0.4.0] — Path 4: site-planner completo — 2026-07-07

### Added
- `HexGridPlacement` (tras el Protocol `PlacementStrategy`): rejilla hexagonal por
  tier con espaciamiento derivado de densidad (T1 1/4 ha, T2 1/10 ha, T3 1/25 ha),
  jitter sembrado ±25 m y reubicación contabilizada cuando la pendiente supera 45° —
  nunca descartes silenciosos. Anemómetros a los sitios más altos (1/10 T1, 1/20 T2/T3).
- `GatewayPlanner`: k-means numpy sembrado (`ceil(n/60)` clusters), snap al punto más
  alto en 200 m, asignación por cercanía (`GW-##`). Metadato puro — ADR-0008.
- `SitePlan`: ensamblaje con estrategia y planner inyectables; emite
  `sensores.geojson` (esquema estable, entrada del Path 5), `gateways.geojson` y
  `site-report.md`; salida **byte-determinista** por semilla — ADR-0007.
- CLI `site-planner generate` (typer) con `--preview` PNG opcional (extra `preview`);
  `config/params.example.yaml`; `PlannerParams` con validación fail-early del YAML.
- `planner/geo.py`: conversión grados↔metros unificada.

### Changed
- `pyproject.toml`: entry point `site-planner`, extra `preview` (matplotlib),
  `types-PyYAML` en dev.

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
