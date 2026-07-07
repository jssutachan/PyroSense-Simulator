# Contrato de datos — Telemetría v1

El payload de telemetría es **el acuerdo congelado** entre los sensores (simulados o
reales) y la plataforma cloud. Modelo fuente: `pyrosense_sim.contracts.telemetry.TelemetryPayload`.
Schema machine-readable: [`payload-schema-v1.json`](payload-schema-v1.json)
(regenerable con `python -m pyrosense_sim.contracts.export_schema > docs/payload-schema-v1.json`;
un test anti-drift garantiza que nunca quede desactualizado).

## Ejemplo

```json
{
  "schema_version": "1.0",
  "device_id": "PYRO-T1-0042",
  "gateway_id": "GW-01",
  "ts_device": "2026-07-07T12:30:00Z",
  "seq": 7,
  "lat": 4.6097,
  "lon": -74.04,
  "elevation_m": 3050.0,
  "temp_c": 18.5,
  "rh_pct": 65.0,
  "smoke_ppm": 0.02,
  "wind_speed_ms": 3.4,
  "wind_dir_deg": 270.0,
  "battery_pct": 88.0,
  "status": "OK"
}
```

## Campo por campo

| Campo | Tipo | Regla de validación | Por qué existe |
|---|---|---|---|
| `schema_version` | str | Literal `"1.0"` | Evolución del contrato por versión, nunca editando v1. Un consumidor sabe exactamente qué forma esperar. |
| `device_id` | str | `^PYRO-T[123]-\d{4}$` | Identidad del nodo; el tier va embebido (T1/T2/T3) para poder filtrar por prioridad sin joins. |
| `gateway_id` | str | `^GW-\d{2,}$` | Qué gateway agregó/retransmitió el mensaje; permite diagnosticar cortes por zona. |
| `ts_device` | datetime UTC | Timezone-aware obligatorio; serializa ISO 8601 con `Z` | **Timestamp del dispositivo**, no de la nube. Comparado con el timestamp de ingesta permite medir latencia extremo-a-extremo y detectar relojes desviados. |
| `seq` | int ≥ 0 | Contador monótono por dispositivo | **Detección de pérdida y duplicados**: un hueco en `seq` = mensajes perdidos; un `seq` repetido = duplicado (MQTT QoS1 puede duplicar). La monotonicidad la verifica el consumidor. |
| `lat` / `lon` | float | −90..90 / −180..180 | Posición del nodo (fija tras despliegue, pero viaja en cada mensaje para que el consumidor no dependa de un registro externo). |
| `elevation_m` | float | — | Elevación del sitio (del DEM); relevante para modelos de propagación. |
| `temp_c` | float | −20..80 | Rango físico sano para la sierra bogotana; fuera de eso es fallo de sensor, no clima. |
| `rh_pct` | float | 0..100 | Humedad relativa. |
| `smoke_ppm` | float | ≥ 0 | Concentración de humo — la señal primaria. |
| `wind_speed_ms` | float \| null | ≥ 0 o `null` | `null` = el nodo no tiene anemómetro (solo algunos tiers lo llevan). **La clave nunca se omite**: forma estable para el parser. |
| `wind_dir_deg` | float \| null | 0..360 o `null` | Ídem. |
| `battery_pct` | float | 0..100 | Salud energética; insumo de `LOW_BATTERY`. |
| `status` | enum | `OK` \| `DEGRADED` \| `LOW_BATTERY` | **Salud del dispositivo, jamás señal de fuego** — ver [ADR-0005](adr/ADR-0005-sensor-no-alerta.md). |

## Reglas transversales

- **Campos desconocidos se rechazan** (`extra="forbid"`): el contrato está blindado en
  ambas direcciones; los bugs de integración fallan rápido y del lado del productor.
- **Payload plano** (sin anidamiento): simplifica el mapeo a columnas en el pipeline de
  analítica y las reglas SQL de IoT Core.
- **Inmutable**: una vez construido y validado, un payload no se muta; cualquier "edición"
  es construir uno nuevo.
