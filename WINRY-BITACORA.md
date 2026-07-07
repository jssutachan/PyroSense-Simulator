# WINRY-BITACORA.md — Estado vivo del proyecto

> Documento canónico del subsistema **PyroSense-Simulator**. Única fuente de verdad sobre el avance.
> Traer (pegar o adjuntar) al inicio de cada sesión; Winry entrega un delta al cerrar.

---

## 1. Identidad del proyecto
- **Nombre del proyecto:** PyroSense — subsistema de simulación (PyroSense-Simulator)
- **Pitch (1 frase):** Simulador de flota de sensores IoT + planificador de sitios sobre DEM que alimenta la plataforma serverless AWS de detección temprana de incendios en los Cerros Orientales de Bogotá.
- **Roles objetivo / vacantes de referencia:** Cloud / Junior DevOps / CloudOps (heredado del proyecto PyroSense global)
- **Fecha de inicio · última actualización:** 2026-07-07 · 2026-07-07

## 2. Arquitectura (resumen)
- **Stack principal:** Python 3.12 (src layout), rasterio/shapely/pyproj (geoespacial), Pydantic (contratos), awsiotsdk (MQTT → AWS IoT Core), uv + ruff + mypy strict + pytest-cov (tooling).
- **Diagrama:** ASCII en `README.md` (site-planner → plan → fleet-sim → MQTT → IoT Core)
- **Repositorio:** `~/Documentos/PyroSense-Simulator` (git local, sin remote aún)

## 3. Métricas de éxito
- [ ] (heredar de la bitácora global de PyroSense — pendiente de traer a esta)

## 4. Criterios de aceptación (definición de "hecho" del subsistema)
- [ ] site-planner produce un plan de despliegue válido desde un DEM real de los Cerros Orientales
- [ ] fleet-sim publica telemetría validada por contrato hacia AWS IoT Core vía MQTT/TLS
- [ ] Cobertura de tests ≥ 85 % con mypy strict y ruff limpios

## 5. Roadmap (etapas y sub-etapas)
> Estado por sub-etapa: ⬜ pendiente · 🟡 en curso · ✅ hecho

| ID | Sub-etapa | Objetivo de aprendizaje | Entregable | Estado |
|----|-----------|-------------------------|------------|--------|
| P1 | Andamiaje del repo y tooling | src layout, packaging moderno (pyproject/hatchling), calidad automatizada (ruff, mypy strict, pytest-cov) | Repo profesional verificado | ✅ |
| P2 | (siguiente path — por definir con el spec) | | | ⬜ |

- **Etapa/sub-etapa actual:** Path 1 completado; listo para Path 2.
- **% de avance global (aprox.):** ~10 % del subsistema simulador.

## 6. Bitácora de sesiones (más reciente arriba)
### Sesión 2026-07-07 — Path 1: andamiaje del repositorio y tooling
- **Logrado:** Árbol completo con src layout; `pyproject.toml` (deps + dev, ruff, mypy strict, pytest con cobertura); `.gitignore` probado con archivos señuelo; `.env.example` sin valores reales; `data/README.md` con dos rutas de descarga del DEM (IGAC / OpenTopography GLO-30); README raíz; smoke test. **Checklist completo verificado en vivo:** `uv pip install -e ".[dev]"` OK, `ruff check` OK, `ruff format --check` OK (10 archivos), `mypy` OK (strict, 5 archivos), `pytest` 1 passed.
- **Aprendizajes:** El sistema solo traía Python 3.10 → se instaló `uv`, que gestiona sus propios intérpretes (descargó CPython 3.12.13) sin sudo ni PPAs. `--cov-fail-under=0` como umbral placeholder que se sube por path.
- **Oportunidades de mejora / deuda técnica:**
  - Las dependencias se dedujeron del dominio porque la "referencia global" no estaba disponible en la sesión → **contrastar contra ese documento antes del Path 2**.
  - No hay CI aún (GitHub Actions con los 4 checks) — candidato natural cuando el repo tenga remote.
  - Umbral de cobertura en 0; subirlo cuando entre lógica real (meta ≥ 85).
- **Próximo paso:** Hacer el commit inicial; traer la referencia global de dependencias y el spec del Path 2.

## 7. Decisiones de arquitectura (ADR)
### ADR-001 — uv como gestor de entorno e intérpretes
- **Contexto:** El proyecto exige Python ≥ 3.12 y la máquina solo tiene 3.10; no hay sudo garantizado.
- **Decisión:** Usar `uv` para venv, resolución de dependencias e instalación del intérprete 3.12.
- **Porqué:** Reproducibilidad sin depender del Python del sistema (Excelencia Operativa); es el estándar actual del ecosistema y defendible en entrevista.
- **Alternativas descartadas:** deadsnakes PPA (requiere sudo, acopla al SO), pyenv (más lento, más fricción).

### ADR-002 — src layout + hatchling
- **Contexto:** El repo crecerá con dos programas y módulos compartidos; los tests deben ejercitar el paquete *instalado*, no el directorio local.
- **Decisión:** `src/pyrosense_sim/` con build backend hatchling e instalación editable.
- **Porqué:** El src layout evita imports accidentales del código sin instalar (bugs de packaging invisibles hasta producción); hatchling es liviano y moderno.
- **Alternativas descartadas:** flat layout (propenso a falsos positivos en tests), setuptools clásico (más boilerplate).

### ADR-003 — Entry points diferidos al Path 2
- **Contexto:** El spec sugiere dos CLIs (site-planner, fleet-sim) que aún no existen.
- **Decisión:** No declarar `[project.scripts]` hasta que existan los módulos reales.
- **Porqué:** Declarar scripts hacia módulos inexistentes instala binarios rotos — el andamiaje no debe mentir sobre lo que ofrece.
- **Alternativas descartadas:** declarar los scripts con stubs vacíos (código muerto que mypy/ruff tendrían que tolerar).

## 8. Preguntas abiertas y deuda técnica viva
- [ ] Contrastar dependencias del `pyproject.toml` contra la "referencia global" del proyecto.
- [ ] ¿Este repo tendrá remote propio en GitHub o será parte de un monorepo PyroSense? (afecta CI y la sección de repositorio del README)
- [ ] Definir CI (GitHub Actions) cuando haya remote.
- [ ] Subir `--cov-fail-under` cuando entre lógica real.

## 9. Datos a re-verificar (caducan)
- Disponibilidad y resolución del DEM en IGAC "Colombia en Mapas" (el catálogo cambia; la Opción B con Copernicus GLO-30 en OpenTopography es el respaldo).
- Versiones pinneadas mínimas en `pyproject.toml` (razonables a 2026-07, revisar al añadir features).
