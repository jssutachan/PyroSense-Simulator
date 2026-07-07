# Revisión de buenas prácticas — consolidación Paths 1–3

**Fecha:** 2026-07-07 · **Rama:** `chore/hardening-p1-p3` · **Alcance:** todo el código de los Paths 1–3.

Veredicto general: la base ya cumplía la mayoría de la checklist porque los principios se
aplicaron desde el diseño, no como parche. Se hicieron **3 refactors quirúrgicos** (ningún
cambio de comportamiento; los 65 tests siguen en verde con 100 % de cobertura).

## B.1 — Diseño orientado a objetos

| Criterio | Estado | Evidencia / acción |
|---|---|---|
| Composición sobre herencia | ✅ Cumplía | Cero jerarquías de herencia en el repo. `Zone`/`ZoneSet`, `TerrainModel` y los publishers son composición pura. La única "herencia" es interface inheritance vía `Protocol`. |
| Inyección de dependencias | ✅ Cumplía | `StdoutPublisher(stream=...)` recibe el stream; `FilePublisher(path, max_bytes)` su destino. Nada intercambia comportamiento heredando. |
| SRP | ✅ Cumplía / ⚠️ 1 ajuste | Datos (`TelemetryPayload`, `Zone`) separados de lógica (`ZoneSet.derive_default`) y de I/O (publishers). Ajuste: `TerrainModel.slope_at` mezclaba dos niveles de abstracción → se extrajo `_neighbourhood()` (`refactor(planner): split slope neighbourhood lookup`). |
| OCP / DIP | ✅ Cumplía | Un publisher nuevo (MQTT en un path futuro) se añade implementando `Publisher`, sin tocar núcleo. Los consumidores dependerán del `Protocol`, no de clases concretas. |
| LSP | ✅ Cumplía | `test_base.py` verifica que ambos publishers concretos satisfacen el `Protocol` (`isinstance` con `runtime_checkable`). |
| ISP | ✅ Cumplía | `Publisher` expone exactamente `publish`/`close`. Nada más. |
| Protocol vs ABC | ✅ Cumplía | `Publisher` es `Protocol` (duck typing estructural): correcto porque no se necesita jerarquía nominal ni implementación compartida. |

## B.2 — Modelado de datos (punto crítico)

| Criterio | Estado | Evidencia / acción |
|---|---|---|
| Pydantic solo en fronteras | ✅ Cumplía | La **única** clase Pydantic del repo es `TelemetryPayload` — exactamente la frontera con la Lambda. Los objetos internos (`Zone` = `@dataclass(frozen=True)`, `TerrainModel` = clase plana sobre numpy) nunca fueron Pydantic, así que no hubo nada que convertir. Trade-off documentado en ADR-0003. |
| Inmutabilidad donde aporta | ✅ Cumplía | `Zone` es frozen (hashable, comparable); `TelemetryPayload` es frozen (un payload emitido no se muta). `ZoneSet` guarda una `tuple`, no una `list`. |
| Dunders útiles | ⚠️ 2 ajustes | `Zone` ya tenía `__repr__`/`__eq__`/`__hash__` generados por dataclass. Faltaban: `TerrainModel.__repr__` (ahora reporta celdas y bounds) y `ZoneSet.__len__`/`__iter__`/`__repr__` (ahora es un contenedor pythónico; antes obligaba a pasar por `.zones`). |

## B.3 — Estilo, tipado y robustez

| Criterio | Estado | Evidencia / acción |
|---|---|---|
| PEP 8 / ruff | ✅ | `ruff check` y `ruff format --check` en verde (reglas E, W, F, I, UP, B, SIM, C4, PT, RUF). |
| mypy --strict sin Any | ✅ | 27 archivos, 0 errores, incluye `tests/`; plugin de pydantic activo; `types-shapely` para narrowing geométrico real. |
| Errores explícitos | ✅ | Cero `except:` desnudos. `ValueError` con mensajes accionables (el fuera-de-rango del DEM imprime el extent completo). Validación en constructores (`max_bytes`, `t1_buffer_m`, CRS ausente) = falla temprana. |
| Métodos pequeños | ✅ tras refactor | Ningún método supera ~25 líneas. |
| Sin efectos secundarios ocultos | ✅ | Cómputo (terrain, zones, contracts) separado de I/O (publishers). `render_schema()` es pura; `main()` es quien imprime. |
| logging vs print | ✅ con nota | El único `print` es el entry point CLI de `export_schema` (justificado: su salida ES el producto). Cuando exista lógica con eventos operativos (fleet-sim), usará `logging`. |
| RNG sembrada | N/A hoy | Aún no hay aleatoriedad. Regla codificada en `CONTRIBUTING.md`: el fleet-sim recibirá un RNG inyectable con semilla configurable. |
| Sin secretos/rutas hardcodeadas | ✅ | Config vía `.env` (ignorado); `.env.example` solo placeholders; tests usan `tmp_path`. |

## B.4 — Tests

- ✅ 65 tests en verde tras el refactor; **100 % de cobertura** (umbral en 90).
- ✅ `tests/` espeja `src/` (`contracts/`, `planner/`, `publishers/`; `fleet/` espera al Path 5).
- ✅ Cero dependencia de archivos externos: los DEM se generan con numpy+rasterio dentro del test.
- ✅ Política extra: warnings de tests = errores (excepción documentada: rasterio/NumPy 2.5).

## Refactors ejecutados (commits atómicos)

1. `refactor(publishers): extract shared NDJSON encoding` — DRY: el formato de línea vivía duplicado en dos publishers; `ndjson_line()` es ahora la única fuente de verdad.
2. `refactor(planner): split slope neighbourhood lookup` — SRP a nivel de método + `__repr__`.
3. `refactor(planner): make ZoneSet a pythonic container` — `__len__`/`__iter__`/`__repr__`.

## Deuda consciente (no se refactorizó, con porqué)

- **`ValueError` en vez de excepciones de dominio propias** (`OutsideDemBoundsError`…): con dos
  puntos de fallo y un solo consumidor, una jerarquía de excepciones sería abstracción prematura
  (YAGNI). Se reevaluará cuando el CLI del planner necesite mapear errores a exit codes.
- **`FilePublisher` no es thread-safe**: el simulador actual es single-thread; se documenta en la
  clase y se revisará si el fleet-sim introduce concurrencia.
