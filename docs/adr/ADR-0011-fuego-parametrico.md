# ADR-0011 — Los eventos de fuego son interpolación paramétrica, no física

**Estado:** Aceptado (Path 6, 2026-07-07)

## Contexto

El simulador necesita "incendios" para validar el pipeline de detección. Existe
ciencia real de propagación (Rothermel, FARSITE, combustibles, pendiente-viento),
compleja y hambrienta de datos que no tenemos (mapas de combustible, humedad del
combustible muerto, etc.).

## Decisión

`FireEvent` es **interpolación paramétrica**: un círculo cuyo radio crece
linealmente, cuyo centro deriva con un vector de viento configurable, y cuya
intensidad (0..1) hace ramp-in suave (smoothstep) tras la ignición y decae
linealmente en un halo más allá del frente. La intensidad escala deltas de señal
(temp↑, rh↓, humo↑↑) sobre la línea base. Nada más.

## Consecuencias

- Produce exactamente lo que el pipeline necesita: **correlación espacial
  multi-sensor plausible** (vecinos ven la firma, lejanos no; la cadencia
  adaptativa se dispara en la zona) con 6 parámetros entendibles.
- El escenario `replay_enero_2024` es una *firma* calibrada del evento real, no
  una reconstrucción — y así se documenta en el propio YAML.
- Límite explícito: este simulador no sirve para estudiar propagación ni para
  planear cortafuegos. Si algún día se necesita, será un componente nuevo
  (¿integración con un modelo externo?) con su propio ADR.

## Alternativas descartadas

- **Modelo físico (Rothermel/FARSITE)**: meses de trabajo y datos inexistentes,
  para un objetivo (probar el pipeline) que no lo requiere.
- **Señales sintéticas sin geometría** (rampas por nodo individual): no produce la
  correlación espacial que la Lambda de detección necesita distinguir de fallos.
