"""NDJSON publisher to stdout. No AWS dependency: useful for smoke runs and piping."""

import sys
from typing import TextIO

from pyrosense_sim.contracts.telemetry import TelemetryPayload
from pyrosense_sim.publishers.ndjson import ndjson_line


class StdoutPublisher:
    """Writes exactly one JSON line per payload to a text stream.

    Example:
        >>> publisher = StdoutPublisher()
        >>> publisher.publish(payload)  # doctest: +SKIP
        {"schema_version":"1.0","device_id":"PYRO-T1-0042",...}
    """

    def __init__(self, stream: TextIO | None = None) -> None:
        """Initialize the publisher.

        Args:
            stream: Destination text stream. Defaults to ``sys.stdout``;
                injecting an ``io.StringIO`` keeps tests trivial.
        """
        self._stream = stream if stream is not None else sys.stdout

    def publish(self, payload: TelemetryPayload) -> None:
        """Write the payload as one NDJSON line and flush.

        Args:
            payload: Validated telemetry payload to emit.
        """
        self._stream.write(ndjson_line(payload))
        self._stream.flush()

    def close(self) -> None:
        """Flush the stream without closing it (the caller/process owns it)."""
        self._stream.flush()
