# ADR-0003 — Pydantic solo en la frontera; dataclasses adentro

**Estado:** Aceptado (Path 2; ratificado en la consolidación, 2026-07-07)

## Contexto

Pydantic da validación y serialización JSON excelentes, pero cobra un costo de CPU y
memoria por instancia (validación en cada construcción, maquinaria de serdes). El
fleet-sim creará muchos objetos internos por tick de simulación.

## Decisión

Pydantic **únicamente** donde el dato cruza la frontera del proceso y necesita
validación/serialización: `TelemetryPayload` (y futuros contratos). Todo objeto
interno — geometrías, estado de nodos, configuraciones ya validadas — usa
`@dataclass` (con `frozen=True` cuando debe ser inmutable/hashable, como `Zone`).

## Consecuencias

- La validación ocurre exactamente una vez, en el borde, donde protege de datos
  externos; adentro los invariantes los garantiza el constructor + mypy strict.
- Los objetos internos son baratos de crear (relevante a miles de ticks) y sin
  dependencia de serialización que no necesitan.
- Regla clara para paths futuros: "¿este objeto sale del proceso o entra desde
  afuera? → Pydantic. ¿Vive y muere adentro? → dataclass."

## Alternativas descartadas

- **Pydantic en todas partes**: uniformidad a cambio de costo por instancia y de
  difuminar dónde está la frontera real del sistema.
- **dicts crudos internos**: sin tipos ni invariantes; mypy no puede ayudar.
