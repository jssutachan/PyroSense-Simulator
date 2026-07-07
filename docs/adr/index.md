# Registro de decisiones de arquitectura (ADRs)

Cada decisión relevante se registra con el formato
**contexto → decisión → consecuencias → alternativas descartadas**.
Un ADR no se edita para cambiar la decisión: se escribe uno nuevo que lo supersede.

| ADR | Decisión | Estado |
|---|---|---|
| [0001](ADR-0001-dos-programas.md) | Dos programas separados: site-planner y fleet-sim | Aceptado |
| [0002](ADR-0002-contrato-primero.md) | Contrato primero; payload v1 congelado | Aceptado |
| [0003](ADR-0003-pydantic-frontera.md) | Pydantic solo en la frontera; dataclasses adentro | Aceptado |
| [0004](ADR-0004-git-flow.md) | Git Flow simplificado (main/develop/feature) | Aceptado |
| [0005](ADR-0005-sensor-no-alerta.md) | El sensor reporta salud del dispositivo, no alertas de fuego | Aceptado |
| [0006](ADR-0006-tooling.md) | Tooling: uv, src layout, mypy strict, cobertura con umbral vivo | Aceptado |
