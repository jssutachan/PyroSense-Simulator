# ADR-0002 — Contrato primero; payload v1 congelado

**Estado:** Aceptado (Path 2, 2026-07-07)

## Contexto

El consumidor del payload (una Lambda tras AWS IoT Core) aún no existe. El simulador
y la plataforma cloud se desarrollarán en paralelo y por personas/repos distintos.

## Decisión

Definir el contrato de telemetría **antes** que cualquier lógica de negocio, congelarlo
como v1 (`schema_version` literal, `extra="forbid"`, modelo frozen) y materializarlo
como JSON Schema versionado en `docs/payload-schema-v1.json` con un test anti-drift.
La evolución es aditiva vía `schema_version` nueva; v1 no se edita jamás.

## Consecuencias

- Los dos lados pueden construirse en paralelo contra el mismo acuerdo verificable.
- Los bugs de integración fallan rápido y del lado del productor (campos desconocidos
  se rechazan), no silenciosamente en el consumidor.
- Costo: cambiar el payload es deliberadamente caro — exige versión nueva. Es una
  fricción aceptada a cambio de estabilidad.

## Alternativas descartadas

- **Schema implícito** ("el JSON que salga del código"): deriva sin control y rompe al
  consumidor sin aviso.
- **`extra="ignore"`**: esconde errores de integración hasta producción.
- **Compartir solo el modelo Python**: acopla al consumidor a Python; el JSON Schema es
  agnóstico de lenguaje.
