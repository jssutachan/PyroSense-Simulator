"""Transport-agnostic publisher interface.

The fleet simulator talks to a ``Publisher`` and never to a concrete
transport, so swapping stdout <-> file <-> AWS IoT Core is a wiring
change, not a code change.
"""

from typing import Protocol, runtime_checkable

from pyrosense_sim.contracts.telemetry import TelemetryPayload


@runtime_checkable
class Publisher(Protocol):
    """Sink for telemetry payloads."""

    def publish(self, payload: TelemetryPayload) -> None:
        """Deliver a single payload."""
        ...

    def close(self) -> None:
        """Release resources. Publishing after close is undefined behavior."""
        ...
