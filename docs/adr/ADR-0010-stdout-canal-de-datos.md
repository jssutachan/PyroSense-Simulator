# ADR-0010 — stdout es el canal de datos; los logs van a stderr

**Estado:** Aceptado (Path 5, 2026-07-07)

## Contexto

`fleet-sim` emite NDJSON por el `StdoutPublisher` **y** necesita logs operativos
(arranque, resumen final, interrupciones). Si ambos comparten stdout, cualquier pipe
(`fleet-sim ... | head`, `... > telemetry.ndjson`) queda contaminado con líneas de log.

## Decisión

Convención Unix estricta: **stdout transporta exclusivamente datos** (una línea NDJSON
por payload); todo log va a **stderr** (`logging.basicConfig(stream=sys.stderr)`), con
`logging` (no `print`) fuera de los entry points.

## Consecuencias

- `fleet-sim run ... > telemetry.ndjson` produce un archivo 100 % parseable, y el
  operador sigue viendo los logs en su terminal.
- El simulador se compone con cualquier herramienta de línea de comandos (jq, head,
  split) sin filtros previos.
- Los tests del CLI distinguen datos de diagnóstico por canal, no por heurísticas.

## Alternativas descartadas

- **Todo a stdout**: rompe los pipes; el consumidor tendría que filtrar logs por regex.
- **Silenciar los logs**: el resumen final y el aviso de SIGINT son parte del valor
  operativo del simulador.
