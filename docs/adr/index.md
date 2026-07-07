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
| [0007](ADR-0007-plan-determinista.md) | El plan de despliegue es determinista por contrato | Aceptado |
| [0008](ADR-0008-gateways-metadato.md) | Gateways como metadato: sin simulación de radio | Aceptado |
| [0009](ADR-0009-ruido-en-el-sensor.md) | El ambiente es verdad de terreno; el ruido vive en el sensor | Aceptado |
| [0010](ADR-0010-stdout-canal-de-datos.md) | stdout es el canal de datos; los logs van a stderr | Aceptado |
| [0011](ADR-0011-fuego-parametrico.md) | Los eventos de fuego son interpolación paramétrica, no física | Aceptado |
| [0012](ADR-0012-fallos-como-decorador.md) | Los fallos se inyectan en el flujo de mensajes, no en los nodos | Aceptado |
| [0013](ADR-0013-qos1-dedupe-en-nube.md) | QoS 1 con deduplicación en la nube | Aceptado |
