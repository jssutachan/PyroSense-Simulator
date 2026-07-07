# ADR-0005 — El sensor reporta salud del dispositivo, no alertas de fuego

**Estado:** Aceptado (Path 2, 2026-07-07)

## Contexto

Al diseñar el payload v1 surgió la pregunta: ¿debe el nodo emitir "fuego detectado"
(un flag o un status `ALERT`)?

## Decisión

No. `status` ∈ {`OK`, `DEGRADED`, `LOW_BATTERY`} describe **salud del hardware**.
La detección de fuego se infiere en la nube a partir de las mediciones crudas
(`temp_c`, `smoke_ppm`, `rh_pct`, viento) de toda la flota.

## Consecuencias

- La lógica de detección vive en un solo lugar (la nube), donde hay contexto de
  vecinos, viento, histórico y cómputo — y donde se puede mejorar sin reflashear
  miles de nodos en un cerro.
- No hay dos fuentes de verdad que puedan contradecirse ("el sensor dice fuego, el
  modelo dice no").
- El payload transporta hechos (mediciones), no juicios — envejece mejor.

## Alternativas descartadas

- **Flag `fire_alert` en el payload**: congela umbrales de detección en el contrato
  (y en firmware), crea alertas contradictorias y duplica mantenimiento.
- **Detección híbrida edge+cloud**: interesante a futuro (latencia), pero exige
  gobernanza de modelos en el edge que hoy no existe; se reevaluará con datos.
