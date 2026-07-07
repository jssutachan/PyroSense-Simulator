# Guía de contribución y estándar de desarrollo

Este documento codifica el estándar obligatorio para **todo path futuro** del
subsistema. Cada path nace cumpliéndolo — nada se "documenta después".

## Flujo de trabajo (Git)

1. Crear rama desde `develop`: `feature/<nombre-descriptivo>` para paths
   (`feature/path-4-site-planner-placement`), `chore/<nombre>` para trabajo transversal.
2. **Conventional Commits atómicos**: prefijo semántico (`feat:`, `fix:`, `refactor:`,
   `test:`, `docs:`, `build:`, `chore:`, `style:`), asunto imperativo ≤ 50 caracteres sin
   punto final, contexto en el cuerpo, referencia a issues/PRs cuando existan.
   Un commit = un cambio lógico coherente (microcommits).
3. Al completar y verificar: merge a `develop` con `--no-ff` (previa confirmación del
   arquitecto). Hito estable = `develop` → `main` + tag (`v0.X-nombre`).
4. Prohibido: `push --force`, borrar ramas o reescribir historia sin autorización explícita.

## Código

- **Python ≥ 3.12**, entorno con `uv` (`uv venv --python 3.12 && uv pip install -e ".[dev]"`).
- Type hints completos; `mypy --strict` limpio (aplica también a `tests/`).
- **Pydantic solo en fronteras** del proceso; objetos internos con `@dataclass`
  (frozen si son value objects) — ver [ADR-0003](adr/ADR-0003-pydantic-frontera.md).
- Composición e inyección de dependencias sobre herencia; interfaces con `Protocol`.
- Excepciones específicas con mensajes accionables; validar en los bordes, fallar temprano.
- Cómputo puro separado de I/O; `logging` (no `print`) fuera de entry points CLI.
- **Toda aleatoriedad con RNG inyectable y semilla configurable** (determinismo
  reproducible; regirá el fleet-sim).
- Cero secretos o rutas absolutas en el código; configuración vía `.env` (ignorado).

## Tests

- `tests/` espeja `src/`; los datos de prueba se **generan sintéticamente** (nunca
  archivos externos ni red).
- Cobertura ≥ el umbral vigente de `pyproject.toml` (sube con el proyecto, no baja).
- Warnings en tests = errores; toda excepción al filtro se documenta con su porqué.

## Documentación (docs-as-code)

Obligatorio **en el mismo trabajo que el código** (mismo PR/rama, nunca "al final"):

- Docstrings **PEP 257 estilo Google** en todo lo público nuevo (`Args:`/`Returns:`/
  `Raises:`/`Example:` cuando aporte); docstring de módulo en cada archivo nuevo.
- Actualizar `README.md`, `docs/architecture.md` y `CHANGELOG.md` si el path cambia
  lo que describen.
- **Un ADR nuevo** (`docs/adr/ADR-XXXX-*.md`) si el path introduce una decisión de
  arquitectura; los ADRs no se editan, se superseden.
- Si cambia el contrato (solo por versión nueva): regenerar
  `docs/payload-schema-v1.json` — el test anti-drift lo exige.

## Verificación final (checklist antes de proponer merge)

```bash
ruff check . && ruff format --check .   # estilo
mypy                                     # tipos (strict, src + tests)
pytest                                   # tests + umbral de cobertura
mkdocs build                             # la documentación construye
```

Los cuatro en verde o no hay merge.
