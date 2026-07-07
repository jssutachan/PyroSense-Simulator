# ADR-0009 — El ambiente es verdad de terreno; el ruido vive en el sensor

**Estado:** Aceptado (Path 5, 2026-07-07)

## Contexto

El spec del motor de flota pedía "ruido gaussiano por nodo con semilla" como parte del
modelo de ambiente. Había dos lugares donde ponerlo: en el `EnvironmentModel` o en el
`SensorNode`.

## Decisión

`EnvironmentModel.conditions_at()` es una **función pura y determinista** de
(posición, elevación, tiempo): representa la verdad física del terreno y no contiene
ningún RNG. El ruido gaussiano sembrado vive en `SensorNode.sample()`: cada nodo
deriva su RNG de `"{seed_escenario}:{device_id}"` (sembrado por string → sha512,
reproducible entre procesos) y perturba sus propias lecturas.

## Consecuencias

- Fidelidad física: en el sistema real el instrumento es lo ruidoso, no la atmósfera.
  Dos nodos vecinos leen la misma verdad con errores independientes — exactamente lo
  que verá la Lambda de detección.
- Determinismo trivial de razonar: los únicos RNG de la simulación están en los nodos,
  y cada stream por nodo es independiente del orden de scheduling.
- El hook de eventos de fuego (Path 6) perturba la verdad de terreno en un solo lugar
  (`conditions_at`), sin tocar el ruido.

## Alternativas descartadas

- **Ruido en el ambiente**: mezcla verdad con medición; el orden de las consultas
  alteraría las series (un RNG compartido) o exigiría un RNG por consulta espacial.
- **Sin ruido**: telemetría artificialmente limpia; la plataforma cloud debe probarse
  contra señales realistas.
