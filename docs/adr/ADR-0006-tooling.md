# ADR-0006 — Tooling: uv, src layout, mypy strict, cobertura con umbral vivo

**Estado:** Aceptado (Path 1, 2026-07-07)

## Contexto

El proyecto exige Python ≥ 3.12; la máquina de desarrollo trae 3.10 y no hay
garantía de sudo. El repo es evidencia de portafolio: el tooling debe ser el de un
equipo profesional actual.

## Decisión

- **uv** gestiona el entorno virtual y el propio intérprete (descarga CPython 3.12).
- **src layout** (`src/pyrosense_sim/`) con build backend **hatchling** e instalación
  editable.
- **mypy strict** sobre `src/` y `tests/`, con plugin de pydantic y stubs
  (`types-shapely`).
- **ruff** para lint + formato (reglas E, W, F, I, UP, B, SIM, C4, PT, RUF).
- **pytest-cov** con umbral que sube con el proyecto (hoy 90; real: 100) y
  **warnings-como-errores** con excepciones documentadas.

## Consecuencias

- Reproducible en cualquier máquina sin tocar el Python del sistema.
- El src layout fuerza a testear el paquete instalado, no el directorio local —
  los bugs de packaging aparecen en desarrollo, no en producción.
- mypy strict convierte errores de diseño en errores de compilación (p. ej. obligó
  al narrowing explícito de geometrías shapely).

## Alternativas descartadas

- **deadsnakes/pyenv**: requieren sudo o son más lentos; acoplan al SO.
- **flat layout**: permite imports accidentales del código sin instalar.
- **setuptools clásico**: más boilerplate sin beneficio aquí.
