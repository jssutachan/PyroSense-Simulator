# ADR-0008 — Gateways como metadato: sin simulación de radio

**Estado:** Aceptado (Path 4, 2026-07-07)

## Contexto

Los nodos reales reportarían vía LoRa a gateways. ¿Debe el planner simular
propagación RF (línea de vista, path loss, Fresnel) para ubicarlos y validar
cobertura?

## Decisión

No. Los gateways son **metadato puro**: `ceil(n/capacidad)` clusters k-means sobre
las posiciones de los nodos, centroide ajustado al punto más alto en 200 m (el único
guiño físico: los gateways reales prefieren sitios elevados), y cada nodo asignado a
su gateway más cercano. La capacidad dimensiona el número de clusters; la asignación
por cercanía puede excederla levemente y así se documenta.

## Consecuencias

- El fleet-sim obtiene lo que necesita (`gateway_id` por nodo para el payload) sin
  que el proyecto se desvíe a un problema de RF que no es su objetivo.
- El k-means propio son ~30 líneas de numpy sembradas — se descartó scikit-learn
  porque costaría más (dependencia pesada, superficie de API) de lo que aporta.
- Si algún día se necesita validar cobertura RF real, será un componente nuevo con
  su propio ADR, no una mutación de este.

## Alternativas descartadas

- **Simulación RF completa**: scope creep; exige datos (clutter, antenas) que no
  existen en este proyecto.
- **Gateways manuales**: válido para operación real, pero el planner debe proponer
  un punto de partida automático.
- **scikit-learn para el clustering**: dependencia desproporcionada al problema.
