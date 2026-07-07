# ADR-0007 — El plan de despliegue es determinista por contrato

**Estado:** Aceptado (Path 4, 2026-07-07)

## Contexto

El site-planner usa aleatoriedad (jitter de posiciones, inicialización de k-means).
Sin control, dos corridas darían planes distintos: imposible de revisar en un diff,
de reproducir un bug, o de citar en un informe.

## Decisión

Toda la aleatoriedad fluye de **una sola semilla configurable** (`seed` en
`params.yaml`), y la serialización es determinista por construcción: sin timestamps,
claves JSON ordenadas, redondeo fijo (coordenadas a 6 decimales ≈ 0.11 m). Mismos
insumos + misma semilla ⇒ archivos **byte-idénticos** (hay un test que compara bytes).

## Consecuencias

- Los planes se pueden versionar y revisar como código: un diff vacío = nada cambió.
- Depuración reproducible; el `site-report.md` registra la semilla usada.
- Regla heredada por el fleet-sim (Path 5): RNG inyectable y sembrada, ya codificada
  en CONTRIBUTING.
- Costo: prohibido introducir fuentes de entropía implícitas (relojes, orden de dicts
  externos, paralelismo no determinista) en el pipeline del plan.

## Alternativas descartadas

- **Aleatoriedad libre** (default de `random`): irreproducible.
- **Congelar la salida como fixture**: fija los bytes pero no la propiedad; cualquier
  cambio legítimo rompería el fixture sin explicar por qué.
