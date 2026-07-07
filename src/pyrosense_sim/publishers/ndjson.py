"""Shared NDJSON encoding for line-oriented publishers.

Single source of truth for how a telemetry payload becomes one NDJSON
line, so every line-oriented publisher (stdout, file) emits exactly the
same bytes for the same payload.
"""

from pyrosense_sim.contracts.telemetry import TelemetryPayload


def ndjson_line(payload: TelemetryPayload) -> str:
    """Encode a payload as one NDJSON line.

    Args:
        payload: The validated telemetry payload to encode.

    Returns:
        The payload as compact JSON followed by a single ``\\n``.
    """
    return payload.model_dump_json() + "\n"
