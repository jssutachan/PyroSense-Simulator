# ADR-0004 — Git Flow simplificado

**Estado:** Aceptado (Consolidación, 2026-07-07)

## Contexto

El proyecto se construye por paths incrementales, con un solo desarrollador (el
arquitecto) asistido por IA, y el repo es evidencia de portafolio: la historia de Git
debe contar el proceso de ingeniería con claridad.

## Decisión

Git Flow simplificado, sin ramas release/hotfix:

- **`main`** — solo estados estables/entregables. Nunca se trabaja directo aquí.
- **`develop`** — rama de integración; nace y muere cada feature aquí.
- **`feature/<nombre-descriptivo>`** — una por path (`feature/path-4-site-planner-placement`);
  nace de `develop`, se mergea a `develop` con `--no-ff` al completar y verificar.
- **`chore/*`** — trabajos transversales (como esta consolidación), mismo ciclo.
- Cuando un conjunto de paths forma un hito estable: `develop` → `main` con tag de
  versión (p. ej. `v0.3-simulator-core`).
- Conventional Commits atómicos; **nunca** `push --force` ni reescritura de historia
  publicada.

## Consecuencias

- Los merges `--no-ff` dejan visible el ciclo de cada feature en el grafo — legible
  para un entrevistador.
- `main` siempre es demoable.
- Costo: más ceremonia que trunk-based; aceptable sin CI/CD maduro y con valor
  didáctico de portafolio.

## Alternativas descartadas

- **Trunk-based development**: óptimo con CI robusta y feature flags; excesivo de
  prerequisitos para esta etapa (la pregunta de cuándo migrar queda abierta).
- **Git Flow completo** (release/hotfix branches): ceremonia sin releases formales aún.
