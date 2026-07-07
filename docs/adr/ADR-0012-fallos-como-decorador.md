# ADR-0012 — Los fallos se inyectan en el flujo de mensajes, no en los nodos

**Estado:** Aceptado (Path 6, 2026-07-07)

## Contexto

El proyecto exige simular patologías de red IoT real (nodos que callan, ráfagas de
reconexión con timestamps viejos, duplicados QoS 1, desorden). ¿Dónde vive esa
lógica? La opción obvia era añadir estados de fallo a `SensorNode`.

## Decisión

`FaultInjector` es un **decorador del protocolo `Publisher`**: implementa
`publish/close`, envuelve cualquier transporte (u otro injector) y perturba el
stream de mensajes. `SensorNode` no se tocó — los nodos siguen comportándose como
hardware sano; lo que falla es *la red y el campo*. El tiempo simulado se lee del
`ts_device` de cada payload, así que el injector no necesita reloj propio.

## Consecuencias

- **Composabilidad real**: fallos sobre baseline, sobre replay de fuego, o
  injectors apilados — sin producto cartesiano de configuraciones en el nodo.
- Separación de dominios: la *medición* (nodo) y el *transporte* (red) fallan de
  formas distintas; el diseño ahora lo refleja. `battery_decay` es el caso límite
  (es del dispositivo) y se implementa reescribiendo el stream, aceptando esa
  pequeña impureza a cambio de mantener un solo seam.
- El backlog de un `burst_reconnect` conserva los `ts_device` originales por
  construcción (los payloads ya viajan con su timestamp) — el caso exacto que la
  Lambda debe distinguir de una alerta real.
- OCP demostrado: el Path 7 (MQTT) recibirá el injector sin cambiar una línea.

## Alternativas descartadas

- **Estados de fallo dentro de `SensorNode`**: mezcla dominios, infla la clase y
  cada fallo nuevo exige tocar el núcleo (viola OCP).
- **Post-procesar el NDJSON**: no sirve para el transporte MQTT en vivo del Path 7.
