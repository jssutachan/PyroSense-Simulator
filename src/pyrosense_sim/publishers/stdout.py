"""NDJSON publisher to stdout. No AWS dependency: useful for smoke runs and piping."""

import sys
from typing import TextIO

from pyrosense_sim.contracts.telemetry import TelemetryPayload


class StdoutPublisher:
    """Writes exactly one JSON line per payload to a text stream.

    The stream defaults to ``sys.stdout``; injecting another ``TextIO``
    keeps the class trivially testable.
    """

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream if stream is not None else sys.stdout

    def publish(self, payload: TelemetryPayload) -> None:
        self._stream.write(payload.model_dump_json() + "\n")
        self._stream.flush()

    def close(self) -> None:
        # The stream is owned by the caller/process; flush but never close it.
        self._stream.flush()
