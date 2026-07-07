# PyroSense Simulator

**Simula la flota de sensores IoT que detecta incendios forestales antes de que sean
noticia** — el subsistema de simulación de PyroSense, una plataforma serverless en AWS
de detección temprana, motivada por los incendios de los Cerros Orientales de Bogotá
de enero de 2024, cuando la detección tardía dejó a la ciudad días bajo el humo.

Este repo responde dos preguntas por software, antes de comprar un solo sensor:
**¿dónde ubicar los nodos?** (site-planner, sobre un modelo digital de elevación real)
y **¿cómo se comporta la plataforma con tráfico de flota realista?** (fleet-sim, que
emite telemetría validada por contrato). La infraestructura AWS vive en su propio repositorio.

## Arquitectura

```mermaid
flowchart LR
    subgraph offline["site-planner (offline, corre una vez)"]
        DEM["DEM GeoTIFF<br/>IGAC / Copernicus"] --> TM[TerrainModel]
        GJ["Zonas GeoJSON<br/>(opcional)"] --> ZS[ZoneSet]
        TM --> PL["Placement (Path 4)"]
        ZS --> PL
        PL --> PLAN["Plan de despliegue<br/>GeoJSON"]
    end

    subgraph online["fleet-sim (long-running)"]
        PLAN --> FE["Motor de flota (Path 5)"]
        FE --> TP["TelemetryPayload v1<br/>contrato congelado"]
        TP --> PUB{Publisher}
    end

    PUB -->|stdout NDJSON| DEV[Desarrollo local]
    PUB -->|file NDJSON| REPLAY[Replay]
    PUB -->|"MQTT/TLS (futuro)"| AWS["AWS IoT Core → Lambda"]
```

La frontera entre este subsistema y la nube es el **[contrato de datos v1](docs/data-contract.md)**:
un payload pydantic congelado, exportado como [JSON Schema](docs/payload-schema-v1.json)
y protegido por un test anti-drift.

## Requisitos e instalación

Python ≥ 3.12. Recomendado con [uv](https://docs.astral.sh/uv/) (gestiona el intérprete solo):

```bash
git clone git@github.com:jssutachan/PyroSense-Simulator.git
cd PyroSense-Simulator
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env        # placeholders; los valores reales nunca se versionan
```

Para el site-planner necesitas un DEM real: sigue [data/README.md](data/README.md)
(IGAC "Colombia en Mapas" o Copernicus GLO-30 vía OpenTopography).

## Uso

Los CLIs `site-planner` y `fleet-sim` llegan con los Paths 4–5. Lo ya disponible:

**Exportar el contrato como JSON Schema** (para el equipo cloud):

```bash
python -m pyrosense_sim.contracts.export_schema > docs/payload-schema-v1.json
```

**Consultar un DEM desde Python:**

```python
from pyrosense_sim.planner.terrain import TerrainModel

terrain = TerrainModel("data/dem_cerros_orientales.tif")
print(terrain)                          # TerrainModel(1200x1100 cells, lon [...], lat [...])
print(terrain.elevation_at(-74.04, 4.61), "m")
print(terrain.slope_at(-74.04, 4.61), "deg")
```

**Clasificar puntos por zona de prioridad:**

```python
from shapely.geometry import box
from pyrosense_sim.planner.zones import ZoneSet

aoi = box(-74.10, 4.50, -74.00, 4.60)
zones = ZoneSet.derive_default(aoi)     # T1 = interfaz urbana occidental (simplificación documentada)
print(zones.tier_of(-74.099, 4.55))     # 1
```

**Emitir telemetría validada a NDJSON:**

```python
from datetime import UTC, datetime
from pyrosense_sim.contracts.telemetry import DeviceStatus, TelemetryPayload
from pyrosense_sim.publishers.stdout import StdoutPublisher

payload = TelemetryPayload(
    device_id="PYRO-T1-0042", gateway_id="GW-01",
    ts_device=datetime.now(UTC), seq=0,
    lat=4.6097, lon=-74.04, elevation_m=3050.0,
    temp_c=18.5, rh_pct=65.0, smoke_ppm=0.02,
    wind_speed_ms=None, wind_dir_deg=None,
    battery_pct=88.0, status=DeviceStatus.OK,
)
StdoutPublisher().publish(payload)
```

**Verificación de calidad** (la checklist completa está en [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)):

```bash
ruff check . && ruff format --check .   # estilo
mypy                                     # tipos (strict, src + tests)
pytest                                   # tests + cobertura (umbral 90, real 100 %)
mkdocs build                             # documentación
mkdocs serve                             # docs en http://127.0.0.1:8000
```

## Estructura del repositorio

```
├── src/pyrosense_sim/
│   ├── contracts/     # Payload v1 (pydantic) + exportador de JSON Schema — LA frontera
│   ├── publishers/    # Protocol Publisher + stdout/file (NDJSON); MQTT llega después
│   ├── planner/       # site-planner: TerrainModel (DEM) y ZoneSet (tiers)
│   └── fleet/         # fleet-sim (Path 5)
├── tests/             # espeja src/; DEMs sintéticos, cero datos externos
├── docs/              # arquitectura, contrato, ADRs, contribución (sitio MkDocs)
├── config/            # configuración de los programas
├── scenarios/         # escenarios de simulación declarativos
└── data/              # DEM real (no versionado) + guía de descarga
```

## Documentación

- **[Guía de arquitectura](docs/architecture.md)** — el diseño completo en 10 minutos.
- **[Contrato de datos v1](docs/data-contract.md)** — campo por campo, con su porqué.
- **[Referencia de API](docs/reference.md)** — generada desde docstrings (`mkdocs serve`).
- **[CHANGELOG](CHANGELOG.md)** — una entrada por path.

## Decisiones de diseño

Registradas como [ADRs](docs/adr/index.md): [dos programas](docs/adr/ADR-0001-dos-programas.md) ·
[contrato primero](docs/adr/ADR-0002-contrato-primero.md) ·
[Pydantic en frontera](docs/adr/ADR-0003-pydantic-frontera.md) ·
[Git Flow](docs/adr/ADR-0004-git-flow.md) ·
[el sensor no alerta](docs/adr/ADR-0005-sensor-no-alerta.md) ·
[tooling](docs/adr/ADR-0006-tooling.md)
