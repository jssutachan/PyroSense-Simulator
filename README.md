# PyroSense Simulator

Subsistema de simulación de **PyroSense**, una plataforma serverless en AWS para
detección temprana de incendios forestales (contexto de referencia: Cerros
Orientales de Bogotá). Este repositorio genera el plan de despliegue de sensores
y simula la flota que alimenta al backend en la nube — no contiene la
infraestructura AWS, que vive en su propio repositorio.

## Arquitectura del subsistema

Dos programas independientes que comparten contratos de mensajes:

```
┌──────────────────┐   plan de despliegue    ┌──────────────────┐
│   site-planner    │ ──────(JSON/YAML)────▶ │    fleet-sim      │
│                   │                        │                   │
│ DEM (GeoTIFF) →   │                        │ genera telemetría │──MQTT/TLS──▶ AWS IoT Core
│ ubicación óptima  │                        │ de N sensores     │
│ de sensores       │                        │ simulados         │
└──────────────────┘                        └──────────────────┘
```

| Módulo (`src/pyrosense_sim/`) | Responsabilidad |
|---|---|
| `planner/` | Site-planner: lee el DEM y calcula ubicaciones de sensores |
| `fleet/` | Fleet-sim: simula la flota y su telemetría |
| `contracts/` | Esquemas de mensajes compartidos con el backend (Pydantic) |
| `publishers/` | Adaptadores de salida: AWS IoT Core (MQTT), stdout, archivo |

## Instalación

Requiere Python **>= 3.12**. Recomendado con [uv](https://docs.astral.sh/uv/):

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
```

O con pip clásico (si ya tienes Python 3.12+):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Configura las variables de entorno:

```bash
cp .env.example .env   # y rellena los valores reales (nunca se versionan)
```

Descarga el DEM siguiendo [data/README.md](data/README.md).

## Cómo correr

> **Placeholder** — los CLIs `site-planner` y `fleet-sim` se implementan en
> paths posteriores.

### Verificación de calidad

```bash
ruff check .            # lint
ruff format --check .   # formato
mypy                    # tipos (modo strict)
pytest                  # tests + cobertura
```

## Estructura del repositorio

```
├── config/       # configuración de los programas
├── scenarios/    # escenarios de simulación declarativos
├── data/         # DEM y datos geoespaciales (no versionados)
├── docs/         # documentación de diseño
├── src/pyrosense_sim/
└── tests/
```

## Decisiones de diseño

<!-- Se documentan aquí a medida que se toman (estilo ADR: contexto → decisión → porqué). -->

- *Pendiente.*
