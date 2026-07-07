# PyroSense Simulator

Subsistema de simulación de **PyroSense**, la plataforma serverless en AWS para
detección temprana de incendios forestales en los Cerros Orientales de Bogotá.

Este sitio documenta el subsistema para dos audiencias:

- **Quien necesita entender el diseño** → empieza por la
  [guía de arquitectura](architecture.md) (10 minutos) y las
  [decisiones de arquitectura](adr/index.md).
- **Quien necesita usar o extender el código** → la
  [referencia de API](reference.md) (generada desde los docstrings) y la
  [guía de contribución](CONTRIBUTING.md).

La pieza más importante del subsistema es el
[contrato de datos v1](data-contract.md): el acuerdo congelado entre los
sensores simulados y la plataforma cloud.

## Estado actual

| Path | Contenido | Estado |
|---|---|---|
| 1 | Andamiaje del repo y tooling de calidad | ✅ |
| 2 | Contrato de telemetría v1 + publishers stdout/file | ✅ |
| 3 | Site-planner: modelo de terreno y zonas prioritarias | ✅ |
| Consolidación | Git Flow, refactor de buenas prácticas, esta documentación | ✅ |
| 4 | Site-planner completo: placement hexagonal, gateways, plan GeoJSON y CLI | ✅ |
| 5+ | Fleet-sim: motor de simulación y publisher MQTT/IoT Core | ⏳ |
