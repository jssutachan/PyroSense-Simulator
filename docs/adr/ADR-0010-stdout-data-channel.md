# ADR-0010 — stdout is the data channel; logs go to stderr

**Status:** Accepted (2026-07-07)

## Context

`fleet-sim` emits NDJSON through the `StdoutPublisher` **and** needs
operational logs (startup, final summary, interrupts). If both share stdout,
any pipe (`fleet-sim ... | head`, `... > telemetry.ndjson`) gets polluted
with log lines.

## Decision

Strict Unix convention: **stdout carries data exclusively** (one NDJSON line
per payload); all logging goes to **stderr**
(`logging.basicConfig(stream=sys.stderr)`), using `logging` (never `print`)
outside CLI entry points.

## Consequences

- `fleet-sim run ... > telemetry.ndjson` produces a 100% parseable file
  while the operator still sees logs in the terminal.
- The simulator composes with any command-line tool (jq, head, split)
  without pre-filtering.
- CLI tests distinguish data from diagnostics by channel, not by heuristics.

## Alternatives considered

- **Everything to stdout**: breaks pipes; consumers would have to filter
  logs with regexes.
- **Silencing the logs**: the final summary and the SIGINT notice are part
  of the simulator's operational value.
