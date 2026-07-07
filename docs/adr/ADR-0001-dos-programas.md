# ADR-0001 — Dos programas separados: site-planner y fleet-sim

**Estado:** Aceptado (Path 1, 2026-07-07)

## Contexto

El subsistema debe (a) decidir dónde ubicar sensores sobre un terreno real y
(b) generar telemetría continua de esa flota hacia la nube. Podría ser un solo
programa que hace ambas cosas.

## Decisión

Dos programas independientes que se comunican por un artefacto intermedio (el plan
de despliegue GeoJSON): **site-planner** (offline, corre una vez) y **fleet-sim**
(long-running).

## Consecuencias

- Ciclos de vida correctos: planificar es un cómputo puntual pesado en geoespacial
  (rasterio/shapely); simular es un proceso de larga duración pesado en I/O. Separados,
  cada uno carga solo sus dependencias y se testea aislado.
- El plan GeoJSON es inspeccionable y versionable: se puede revisar a mano, regenerar,
  o editar antes de simular.
- El fleet-sim puede correr con un plan hecho a mano (sin DEM) — útil para pruebas.

## Alternativas descartadas

- **Monolito con subcomandos**: acopla dependencias (el simulador arrastraría rasterio)
  y mezcla ciclos de vida.
- **Planificación en línea dentro del simulador**: repetiría un cómputo costoso e
  impediría inspeccionar/ajustar el plan entre etapas.
