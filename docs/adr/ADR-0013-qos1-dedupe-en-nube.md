# ADR-0013 — QoS 1 con deduplicación en la nube

**Estado:** Aceptado (Path 7, 2026-07-07)

## Contexto

MQTT ofrece tres niveles de entrega: QoS 0 (at-most-once, puede perder), QoS 1
(at-least-once, puede duplicar) y QoS 2 (exactly-once, handshake de 4 vías).
Para telemetría de detección de incendios, perder mensajes es inaceptable; ¿y
los duplicados?

## Decisión

**QoS 1** en el `MqttPublisher`, y la **deduplicación por `device_id` + `seq`
es responsabilidad de la nube**, no del productor. El payload v1 ya carga todo
lo necesario (`seq` monótono por dispositivo) desde el Path 2 — esta decisión
estaba sembrada en el contrato.

## Consecuencias

- Nunca se pierde una lectura por diseño del transporte (crítico en alertas);
  el costo es que la Lambda debe ser **idempotente** ante `device_id`+`seq`
  repetidos.
- AWS IoT Core no soporta QoS 2, así que exactly-once ni siquiera era opción
  real — pretenderlo en el cliente sería mentirle al sistema.
- El simulador *entrena* esta responsabilidad: el fallo `duplicates` (Path 6)
  produce exactamente los duplicados que la nube deberá absorber.
- Coherencia extremo a extremo: red at-least-once + consumidor idempotente es
  el patrón estándar de sistemas distribuidos (mismo contrato que SQS
  standard, Kinesis, etc.).

## Alternativas descartadas

- **QoS 0**: pérdida silenciosa de lecturas en la red menos confiable del
  sistema (radio en un cerro); inaceptable para el caso de uso.
- **QoS 2**: no existe en IoT Core; y aun existiendo, el costo de latencia y
  estado por mensaje no compra nada que la idempotencia no dé más barato.
- **Dedupe en el cliente**: el cliente no puede deduplicar lo que la red
  duplica después de él; solo la nube ve el stream final.
