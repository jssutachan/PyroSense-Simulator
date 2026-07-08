# Best-practices review — foundation hardening

**Date:** 2026-07-07 · **Branch:** `chore/hardening-p1-p3` · **Scope:** the
foundation modules (data contract, publishers, terrain and zones).

Overall verdict: the codebase already met most of the checklist because the
principles were applied at design time, not as an afterthought. **Three
surgical refactors** were applied (no behavior changes; the full test suite
stayed green at 100% coverage).

## Object-oriented design

| Criterion | Status | Evidence / action |
|---|---|---|
| Composition over inheritance | ✅ Already compliant | Zero inheritance hierarchies. `Zone`/`ZoneSet`, `TerrainModel` and the publishers are pure composition. The only "inheritance" is interface inheritance via `Protocol`. |
| Dependency injection | ✅ Already compliant | `StdoutPublisher(stream=...)` receives its stream; `FilePublisher(path, max_bytes)` its destination. Nothing swaps behavior through inheritance. |
| Single responsibility | ✅ / ⚠️ 1 fix | Data (`TelemetryPayload`, `Zone`) separated from logic (`ZoneSet.derive_default`) and from I/O (publishers). Fix: `TerrainModel.slope_at` mixed two abstraction levels → `_neighbourhood()` extracted. |
| Open/closed & dependency inversion | ✅ Already compliant | A new publisher (e.g., MQTT) is added by implementing `Publisher`, without touching the core. Consumers depend on the `Protocol`, not concrete classes. |
| Liskov substitution | ✅ Already compliant | Tests verify every concrete publisher satisfies the `Protocol` (`isinstance` with `runtime_checkable`). |
| Interface segregation | ✅ Already compliant | `Publisher` exposes exactly `publish`/`close`. Nothing else. |
| Protocol vs ABC | ✅ Already compliant | `Publisher` is a `Protocol` (structural duck typing): correct because no nominal hierarchy or shared implementation is needed. |

## Data modeling

| Criterion | Status | Evidence / action |
|---|---|---|
| Pydantic only at boundaries | ✅ Already compliant | The **only** pydantic classes are boundary objects (`TelemetryPayload`; later, scenario and settings). Internal objects (`Zone` = `@dataclass(frozen=True)`, `TerrainModel` = plain class over numpy) were never pydantic. Trade-off documented in ADR-0003. |
| Immutability where it pays | ✅ Already compliant | `Zone` is frozen (hashable, comparable); `TelemetryPayload` is frozen (an emitted payload is never mutated). `ZoneSet` stores a `tuple`, not a `list`. |
| Useful dunder methods | ⚠️ 2 fixes | `Zone` already had dataclass-generated `__repr__`/`__eq__`/`__hash__`. Missing: `TerrainModel.__repr__` (now reports cells and bounds) and `ZoneSet.__len__`/`__iter__`/`__repr__` (now a pythonic container; it previously forced access through `.zones`). |

## Style, typing and robustness

| Criterion | Status | Evidence / action |
|---|---|---|
| PEP 8 via ruff | ✅ | `ruff check` and `ruff format --check` green (rules E, W, F, I, UP, B, SIM, C4, PT, RUF). |
| Strict mypy, no implicit Any | ✅ | Zero errors including `tests/`; pydantic plugin active; `types-shapely` for real geometry narrowing. |
| Explicit error handling | ✅ | Zero bare `except:`. `ValueError` with actionable messages (the DEM out-of-bounds error prints the full valid extent). Constructor validation (`max_bytes`, `t1_buffer_m`, missing CRS) = fail early. |
| Small, single-purpose methods | ✅ after refactor | No method exceeds ~25 lines. |
| No hidden side effects | ✅ | Computation (terrain, zones, contracts) separated from I/O (publishers). `render_schema()` is pure; `main()` does the printing. |
| logging vs print | ✅ with a note | The only `print` is the `export_schema` CLI entry point (justified: its output IS the product). Operational events use `logging`. |
| Seeded randomness | ✅ | Every RNG is injectable and seeded (a hard rule in the contributing guide). |
| No secrets / hardcoded paths | ✅ | Config via `.env` (git-ignored); `.env.example` has placeholders only; tests use `tmp_path`. |

## Tests

- ✅ Full suite green after the refactor, at **100% coverage** at the time of
  review (threshold: 90).
- ✅ `tests/` mirrors `src/`.
- ✅ Zero external-file dependencies: DEMs are generated with numpy+rasterio
  inside each test.
- ✅ Extra policy: test warnings are errors (documented exception:
  rasterio/NumPy 2.5).

## Refactors applied (atomic commits)

1. `refactor(publishers): extract shared NDJSON encoding` — DRY: the line
   format lived duplicated in two publishers; `ndjson_line()` is now the
   single source of truth.
2. `refactor(planner): split slope neighbourhood lookup` — method-level SRP
   plus an informative `__repr__`.
3. `refactor(planner): make ZoneSet a pythonic container` —
   `__len__`/`__iter__`/`__repr__`.

## Conscious debt (not refactored, with reasons)

- **`ValueError` instead of custom domain exceptions**
  (`OutsideDemBoundsError`…): with two failure points and a single consumer,
  an exception hierarchy would be premature abstraction (YAGNI). To be
  revisited if CLI error-to-exit-code mapping ever needs it.
- **`FilePublisher` is not thread-safe**: the simulator is single-threaded
  by design; documented on the class, revisited if concurrency ever lands.
